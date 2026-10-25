"""
File: 05_data_mining.py
Mô tả: Giai đoạn 5 - Khai phá dữ liệu chuyên sâu (Data Mining & Machine Learning):
       1. Phân khúc khách hàng RFM (Rule-based) & Phân cụm K-Means Clustering.
       2. Phân tích giỏ hàng (Market Basket Analysis) với thuật toán Apriori/FP-Growth.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from mlxtend.frequent_patterns import apriori, association_rules
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine

OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# ==============================================================================
# PHẦN 1: PHÂN KHÚC KHÁCH HÀNG RFM (RECENCY - FREQUENCY - MONETARY)
# ==============================================================================
def rfm_segmentation_and_clustering(conn, output_csv):
    print("\n" + "=" * 70)
    print("PHẦN 1: MÔ HÌNH PHÂN KHÚC KHÁCH HÀNG RFM & PHÂN CỤM K-MEANS")
    print("=" * 70)

    # 1. Trích xuất dữ liệu giao dịch của khách hàng định danh từ Fact_Sales
    query = """
    SELECT 
        c.CustomerID,
        c.CustomerCode,
        c.Country,
        f.InvoiceNo,
        f.InvoiceTimestamp,
        f.TotalRevenue
    FROM Fact_Sales f
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE c.IsGuestCustomer = 0
    """
    df_sales = pd.read_sql_query(text(query), conn)
    df_sales.columns = [
        "CustomerID", "CustomerCode", "Country", "InvoiceNo",
        "InvoiceTimestamp", "TotalRevenue"
    ]
    df_sales['InvoiceTimestamp'] = pd.to_datetime(df_sales['InvoiceTimestamp'])

    # 2. Xác định ngày mốc tham chiếu (Snapshot Date = Ngày max + 1)
    snapshot_date = df_sales['InvoiceTimestamp'].max() + pd.Timedelta(days=1)
    print(f"- Ngày mốc phân tích (Snapshot Date): {snapshot_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"- Tổng số giao dịch phân tích: {len(df_sales):,} dòng")
    print(f"- Tổng số khách hàng định danh: {df_sales['CustomerID'].nunique():,} khách hàng")

    # 3. Tính toán 3 chỉ số R, F, M
    rfm = df_sales.groupby('CustomerID').agg(
        Country=('Country', 'first'),
        CustomerCode=('CustomerCode', 'first'),
        LastPurchaseDate=('InvoiceTimestamp', 'max'),
        Frequency=('InvoiceNo', 'nunique'),
        Monetary=('TotalRevenue', 'sum')
    ).reset_index()

    rfm['Recency'] = (snapshot_date - rfm['LastPurchaseDate']).dt.days
    rfm['Monetary'] = rfm['Monetary'].round(2)

    print("\nThống kê mô tả chỉ số RFM:")
    print(rfm[['Recency', 'Frequency', 'Monetary']].describe().round(2))

    # 4. Chấm điểm ngũ vị phân (Quantiles 1 - 5)
    # Recency: Số ngày càng nhỏ -> Điểm càng cao (5 là mới mua gần đây nhất)
    # Frequency, Monetary: Giá trị càng lớn -> Điểm càng cao
    rfm['R_Score'] = pd.qcut(rfm['Recency'], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['RFM_Group'] = rfm['R_Score'].astype(str) + rfm['F_Score'].astype(str) + rfm['M_Score'].astype(str)
    rfm['RFM_Score'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']

    # 5. Phân nhóm khách hàng theo chuẩn nghiệp vụ (Rule-Based RFM Segmentation)
    def assign_rfm_segment(row):
        r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
        if r >= 4 and f >= 4 and m >= 4:
            return 'Champions (VIP)'
        elif r >= 3 and f >= 3 and m >= 3:
            return 'Loyal Customers (Trung thành)'
        elif r >= 4 and f <= 2:
            return 'New / Potential Loyalists (Mới & Tiềm năng)'
        elif r >= 3 and f <= 3:
            return 'Promising (Hứa hẹn)'
        elif r == 2 and f >= 3:
            return 'At Risk (Có nguy cơ rời bỏ)'
        elif r == 1 and f >= 4:
            return "Can't Lose Them (VIP sắp mất)"
        elif r <= 2 and f <= 2:
            return 'Hibernating / Lost (Ngủ đông / Đã mất)'
        else:
            return 'Need Attention (Cần chăm sóc)'

    rfm['Segment'] = rfm.apply(assign_rfm_segment, axis=1)

    print("\nPhân bổ số lượng khách hàng theo từng phân khúc RFM:")
    segment_summary = rfm.groupby('Segment').agg(
        CustomerCount=('CustomerID', 'count'),
        AvgRecency=('Recency', 'mean'),
        AvgFrequency=('Frequency', 'mean'),
        AvgMonetary=('Monetary', 'mean'),
        TotalRevenue=('Monetary', 'sum')
    ).round(2).sort_values(by='TotalRevenue', ascending=False)
    
    segment_summary['CustomerShare_Pct'] = (segment_summary['CustomerCount'] / len(rfm) * 100).round(2)
    segment_summary['RevenueShare_Pct'] = (segment_summary['TotalRevenue'] / rfm['Monetary'].sum() * 100).round(2)
    print(segment_summary[['CustomerCount', 'CustomerShare_Pct', 'TotalRevenue', 'RevenueShare_Pct', 'AvgRecency', 'AvgFrequency', 'AvgMonetary']])

    # 6. Gom cụm K-Means Clustering
    print("\nTiến hành gom cụm không giám sát K-Means Clustering...")
    # Log transformation xử lý lệch phải (skewness)
    rfm_log = pd.DataFrame()
    rfm_log['Recency'] = np.log1p(rfm['Recency'])
    rfm_log['Frequency'] = np.log1p(rfm['Frequency'])
    rfm_log['Monetary'] = np.log1p(rfm['Monetary'].clip(lower=0))

    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_log)

    # 6.1 Elbow Method (WCSS / Inertia) + Silhouette Score cho k = 2 → 8
    k_range = range(2, 9)
    wcss_values = []
    silhouette_values = []
    print("\n  Phân tích Elbow Method (WCSS) & Silhouette Score cho k = 2 → 8:")
    print(f"  {'k':>3} | {'WCSS (Inertia)':>16} | {'Silhouette Score':>18}")
    print("  " + "-" * 45)
    for k in k_range:
        km_test = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km_test.fit_predict(rfm_scaled)
        wcss = km_test.inertia_
        sil = silhouette_score(rfm_scaled, labels)
        wcss_values.append(wcss)
        silhouette_values.append(sil)
        print(f"  {k:>3} | {wcss:>16,.2f} | {sil:>18.4f}")

    # Xác định số cụm theo Silhouette; giữ k=4 nếu gần bằng nghiệm tốt nhất.
    best_k = list(k_range)[np.argmax(silhouette_values)]
    best_sil = max(silhouette_values)
    k4_index = 4 - k_range.start
    if silhouette_values[k4_index] >= best_sil * 0.95:
        best_k = 4

    # Vẽ biểu đồ Elbow + Silhouette (kép trên 1 figure)
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Elbow chart
    ax1.plot(list(k_range), wcss_values, 'bo-', linewidth=2, markersize=8)
    ax1.axvline(x=best_k, color='red', linestyle='--', alpha=0.7, label=f'k = {best_k} (Selected)')
    ax1.set_xlabel('Số cụm (k)', fontsize=12)
    ax1.set_ylabel('WCSS (Inertia)', fontsize=12)
    ax1.set_title('Elbow Method — Chọn số cụm tối ưu', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Silhouette chart
    ax2.plot(list(k_range), silhouette_values, 'gs-', linewidth=2, markersize=8)
    ax2.axvline(x=best_k, color='red', linestyle='--', alpha=0.7, label=f'k = {best_k} (Selected)')
    ax2.set_xlabel('Số cụm (k)', fontsize=12)
    ax2.set_ylabel('Silhouette Score', fontsize=12)
    ax2.set_title('Silhouette Analysis — Đánh giá chất lượng cụm', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    elbow_chart_path = os.path.join(OUTPUTS_DIR, 'elbow_silhouette_chart.png')
    plt.savefig(elbow_chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Đã lưu biểu đồ Elbow & Silhouette vào: '{elbow_chart_path}'")

    print(f"  → Số cụm được chọn: k = {best_k} (Silhouette = {silhouette_values[best_k - 2]:.4f})")

    # 6.2 Kiểm tra độ ổn định cụm (Cluster Stability) qua nhiều random seeds
    print(f"\n  Kiểm tra độ ổn định cụm K-Means (Stability Test, k={best_k}, 5 seeds):")
    stability_labels = []
    stability_seeds = [0, 7, 42, 123, 2024]
    for seed in stability_seeds:
        km_stab = KMeans(n_clusters=best_k, random_state=seed, n_init=10)
        stab_labels = km_stab.fit_predict(rfm_scaled)
        stability_labels.append(stab_labels)
        sil_stab = silhouette_score(rfm_scaled, stab_labels)
        print(f"    Seed {seed:>5}: Silhouette = {sil_stab:.4f}")

    # Tính tỷ lệ khách hàng được phân vào cùng một cụm giữa các seed
    from collections import Counter
    ref_labels = stability_labels[0]
    agreement_rates = []
    for i in range(1, len(stability_labels)):
        # Sử dụng mapping tối ưu giữa cụm để so sánh (greedy matching by size)
        from scipy.optimize import linear_sum_assignment
        contingency = np.zeros((best_k, best_k), dtype=int)
        for j in range(len(ref_labels)):
            contingency[ref_labels[j], stability_labels[i][j]] += 1
        row_ind, col_ind = linear_sum_assignment(-contingency)
        agreement = sum(contingency[r, c] for r, c in zip(row_ind, col_ind)) / len(ref_labels)
        agreement_rates.append(agreement)
    avg_agreement = np.mean(agreement_rates)
    print(f"  → Tỷ lệ đồng thuận trung bình giữa các seed: {avg_agreement:.2%}")
    if avg_agreement >= 0.90:
        print("  ✅ Cụm ổn định (>= 90% đồng thuận).")
    else:
        print("  ⚠️ Cụm có thể không ổn định (< 90% đồng thuận).")

    # 6.3 Áp dụng K-Means với k tối ưu đã chọn
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    rfm['KMeans_Cluster'] = kmeans.fit_predict(rfm_scaled)

    # Đặt tên cụm dựa trên Monetary trung bình
    cluster_monetary = rfm.groupby('KMeans_Cluster')['Monetary'].mean().sort_values()
    cluster_rank = {cluster: idx for idx, cluster in enumerate(cluster_monetary.index)}
    value_names = {
        2: ['Lower Value', 'Higher Value'],
        3: ['Low Value', 'Moderate Value', 'High Value'],
        4: ['Low Value', 'Moderate Value', 'High Value', 'Super VIP']
    }.get(best_k, [f'Value Tier {rank + 1}' for rank in range(best_k)])
    cluster_labels = {
        rank: f'Cluster {rank + 1} - {value_name}'
        for rank, value_name in enumerate(value_names)
    }
    rfm['KMeans_Label'] = rfm['KMeans_Cluster'].map(cluster_rank).map(cluster_labels)

    # 6.4 Vẽ biểu đồ phân bố cụm K-Means (Scatter plot 2D: Frequency vs Monetary)
    fig2, ax3 = plt.subplots(figsize=(10, 7))
    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
    for cluster_id in sorted(rfm['KMeans_Cluster'].unique()):
        mask = rfm['KMeans_Cluster'] == cluster_id
        rank = cluster_rank.get(cluster_id, cluster_id)
        label = cluster_labels.get(rank, f'Cluster {cluster_id}')
        color = colors[rank] if rank < len(colors) else '#95a5a6'
        ax3.scatter(
            np.log1p(rfm.loc[mask, 'Frequency']),
            np.log1p(rfm.loc[mask, 'Monetary'].clip(lower=0)),
            c=color, label=label, alpha=0.6, s=30, edgecolors='white', linewidth=0.3
        )
    ax3.set_xlabel('log(1 + Frequency)', fontsize=12)
    ax3.set_ylabel('log(1 + Monetary)', fontsize=12)
    ax3.set_title(f'Phân bố cụm K-Means (k={best_k}) trên không gian RFM', fontsize=13, fontweight='bold')
    ax3.legend(title='Cụm khách hàng', fontsize=9, title_fontsize=10)
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    scatter_path = os.path.join(OUTPUTS_DIR, 'kmeans_clusters_scatter.png')
    plt.savefig(scatter_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Đã lưu biểu đồ phân bố cụm K-Means vào: '{scatter_path}'")

    # Lưu kết quả RFM
    rfm.to_csv(output_csv, index=False)
    print(f"\n=> Đã lưu kết quả phân khúc khách hàng vào: '{output_csv}'")
    return rfm


# ==============================================================================
# PHẦN 2: PHÂN TÍCH GIỎ HÀNG (MARKET BASKET ANALYSIS - APRIORI)
# ==============================================================================
def market_basket_analysis(conn, output_csv, min_support=0.015, min_lift=1.2):
    print("\n" + "=" * 70)
    print("PHẦN 2: PHÂN TÍCH GIỎ HÀNG (MARKET BASKET ANALYSIS - APRIORI)")
    print("=" * 70)

    # 1. Trích xuất giao dịch chi tiết theo từng hóa đơn
    # Loại trừ các mã cước phí, vận chuyển không phải hàng lưu niệm
    exclude_items = ['POSTAGE', 'DOTCOM POSTAGE', 'MANUAL', 'DISCOUNT', 'AMAZON FEE', 'NO DESCRIPTION']
    
    query = """
    SELECT 
        f.InvoiceNo,
        p.Description
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    WHERE p.Description NOT IN ({})
    """.format(", ".join(f"'{x}'" for x in exclude_items))

    df_items = pd.read_sql_query(text(query), conn)
    df_items.columns = ["InvoiceNo", "Description"]
    print(f"- Số dòng mặt hàng phân tích: {len(df_items):,}")
    
    # Lọc các đơn hàng có từ 2 sản phẩm trở lên
    order_item_counts = df_items.groupby('InvoiceNo')['Description'].nunique()
    valid_invoices = order_item_counts[order_item_counts >= 2].index
    df_filtered = df_items[df_items['InvoiceNo'].isin(valid_invoices)]
    print(f"- Số hóa đơn hợp lệ (có >= 2 sản phẩm): {len(valid_invoices):,} đơn hàng")

    # 2. Xây dựng ma trận nhị phân (One-hot encoded Transaction Matrix)
    print("  -> Đang xây dựng ma trận giỏ hàng One-Hot Transaction Matrix...")
    basket = (df_filtered.groupby(['InvoiceNo', 'Description'])['Description']
              .count().unstack().reset_index().fillna(0)
              .set_index('InvoiceNo'))
    
    # Chuyển đổi sang kiểu bool (True/False) theo chuẩn mới của mlxtend
    basket_sets = (basket > 0)
    print(f"     + Kích thước ma trận giỏ hàng: {basket_sets.shape[0]:,} đơn hàng x {basket_sets.shape[1]:,} sản phẩm")

    # 3. Chạy thuật toán Apriori tìm tập phổ biến
    print(f"  -> Đang chạy thuật toán Apriori với min_support = {min_support} ({min_support*100:.1f}%)...")
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
    frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
    print(f"     + Tìm thấy {len(frequent_itemsets):,} tập sản phẩm phổ biến!")

    # 4. Khai phá các luật kết hợp (Association Rules)
    print(f"  -> Đang sinh các luật kết hợp (Association Rules) với Lift >= {min_lift}...")
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # Định dạng chuỗi tập hợp rõ ràng để lưu trữ và hiển thị
    rules['antecedents_str'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules['consequents_str'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
    
    # Sắp xếp theo Lift và Confidence
    rules = rules.sort_values(by=['lift', 'confidence'], ascending=[False, False])
    
    print(f"\n=> Đã khai phá thành công {len(rules):,} luật kết hợp có ý nghĩa kinh doanh!")
    print("\nTOP 10 LUẬT KẾT HỢP GỢI Ý BÁN CHÉO MẠNH NHẤT (HIGHEST LIFT):")
    print("-" * 70)
    top_10_rules = rules.head(10)
    for idx, row in top_10_rules.iterrows():
        print(f"Luật {idx + 1}:")
        print(f"  - Nếu khách mua [A]: {row['antecedents_str']}")
        print(f"  - Gợi ý mua thêm [B]: {row['consequents_str']}")
        print(f"  - Support: {row['support']*100:.2f}% | Confidence: {row['confidence']*100:.2f}% | Lift: {row['lift']:.2f}")
        print()

    # Lưu kết quả
    rules_to_save = rules[['antecedents_str', 'consequents_str', 'antecedent support', 'consequent support', 
                           'support', 'confidence', 'lift', 'leverage', 'conviction']]
    rules_to_save.to_csv(output_csv, index=False)
    print(f"=> Đã lưu toàn bộ các luật kết hợp vào: '{output_csv}'")
    return rules


# ==============================================================================
# HÀM CHÍNH ĐIỀU PHỐI (MAIN RUNNER)
# ==============================================================================
def run_data_mining():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    rfm_output = os.path.join(OUTPUTS_DIR, "rfm_customer_segments.csv")
    basket_output = os.path.join(OUTPUTS_DIR, "market_basket_rules.csv")
    engine = get_engine()
    with engine.connect() as conn:
        rfm_segmentation_and_clustering(conn, rfm_output)
        market_basket_analysis(conn, basket_output, min_support=0.015, min_lift=1.2)
    print("\n" + "=" * 70)
    print("HOÀN THÀNH TOÀN BỘ GIAI ĐOẠN 5: KHAI PHÁ DỮ LIỆU & MACHINE LEARNING!")
    print("=" * 70)

if __name__ == '__main__':
    run_data_mining()
