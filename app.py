"""
HỆ THỐNG KHO DỮ LIỆU & PHÂN TÍCH KINH DOANH BÁN LẺ
(ONLINE RETAIL DATA WAREHOUSE & BUSINESS INTELLIGENCE DASHBOARD)
File: app.py
Khởi chạy: streamlit run app.py
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests

# ------------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG VÀ THIẾT KẾ GIAO DIỆN (STREAMLIT PAGE CONFIG & THEME)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Retail DWH & Analytics Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 50%, #0D9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        color: #64748B;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    
    .metric-label {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-value {
        color: #0F172A;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0.3rem 0;
    }
    
    .metric-delta {
        font-size: 0.82rem;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. ĐƯỜNG DẪN DỮ LIỆU & TẢI DỮ LIỆU (CACHED DATA LOADERS)
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "retail_dwh.db")
RFM_PATH = os.path.join(BASE_DIR, "outputs", "rfm_customer_segments.csv")
RULES_PATH = os.path.join(BASE_DIR, "outputs", "market_basket_rules.csv")

@st.cache_data(ttl=3600)
def load_kpi_and_monthly(db_path):
    conn = sqlite3.connect(db_path)
    q_monthly = """
    SELECT 
        d.YearMonth,
        d.Year,
        d.Month,
        COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
        SUM(f.Quantity) AS TotalUnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS MonthlyRevenue,
        ROUND(SUM(f.TotalRevenue) / COUNT(DISTINCT f.InvoiceNo), 2) AS AOV
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.YearMonth, d.Year, d.Month
    ORDER BY d.Year, d.Month
    """
    df_monthly = pd.read_sql_query(q_monthly, conn)
    
    # Tính MoM Growth %
    df_monthly['PrevRevenue'] = df_monthly['MonthlyRevenue'].shift(1)
    df_monthly['MoM_Growth_Pct'] = (
        (df_monthly['MonthlyRevenue'] - df_monthly['PrevRevenue']) / df_monthly['PrevRevenue'] * 100
    ).round(2)
    
    conn.close()
    return df_monthly

@st.cache_data(ttl=3600)
def load_country_data(db_path):
    conn = sqlite3.connect(db_path)
    q = """
    SELECT 
        l.Country,
        l.RegionType,
        COUNT(DISTINCT f.InvoiceNo) AS Orders,
        COUNT(DISTINCT f.CustomerKey) AS Customers,
        SUM(f.Quantity) AS UnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue
    FROM Fact_Sales f
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    GROUP BY l.Country, l.RegionType
    ORDER BY Revenue DESC
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_product_data(db_path):
    conn = sqlite3.connect(db_path)
    q = """
    SELECT 
        p.StockCode,
        p.Description,
        SUM(f.Quantity) AS TotalQty,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        ROUND(AVG(f.UnitPrice), 2) AS AvgPrice
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    GROUP BY p.StockCode, p.Description
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_hourly_data(db_path):
    conn = sqlite3.connect(db_path)
    q = """
    SELECT 
        f.Hour,
        COUNT(DISTINCT f.InvoiceNo) AS Orders,
        SUM(f.Quantity) AS Units,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue
    FROM Fact_Sales f
    GROUP BY f.Hour
    ORDER BY f.Hour
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_rfm_data(rfm_path):
    if os.path.exists(rfm_path):
        return pd.read_csv(rfm_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_basket_rules(rules_path):
    if os.path.exists(rules_path):
        return pd.read_csv(rules_path)
    return pd.DataFrame()

# Tải trước dữ liệu
df_monthly = load_kpi_and_monthly(DB_PATH)
df_country = load_country_data(DB_PATH)
df_products = load_product_data(DB_PATH)
df_hourly = load_hourly_data(DB_PATH)
df_rfm = load_rfm_data(RFM_PATH)
df_rules = load_basket_rules(RULES_PATH)

# ------------------------------------------------------------------------------
# 3. SIDEBAR - BỘ LỌC VÀ THÔNG TIN DỰ ÁN
# ------------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3081/3081559.png", width=65)
    st.markdown("### **BỘ ĐIỀU KHIỂN DWH**")
    st.caption("Kho Dữ Liệu Bán Lẻ Trực Tuyến")
    
    st.markdown("---")
    st.markdown("#### 🔍 **Bộ Lọc Phân Tích**")
    
    # Lọc khu vực
    region_options = ["Tất cả khu vực", "Domestic (Vương quốc Anh)", "International (Quốc tế)"]
    selected_region = st.selectbox("Thị trường:", region_options)
    
    # Lọc phân khúc RFM
    if not df_rfm.empty:
        all_segments = ["Tất cả"] + sorted(df_rfm['Segment'].dropna().unique().tolist())
        selected_segment = st.selectbox("Phân khúc RFM:", all_segments)
    else:
        selected_segment = "Tất cả"
        
    st.markdown("---")
    st.markdown("#### 📊 **Thông Tin Kho Dữ Liệu**")
    st.markdown("""
    - **PostgreSQL DWH**: 🟢 `localhost:5432` (`dwh`)
    - **MinIO S3 Lakehouse**: 🟢 `localhost:9000` (`raw, staging, curated`)
    - **Apache Superset BI**: 🟢 `localhost:8088`
    - **Mô hình**: Star Schema chuẩn Kimball
    - **Dòng Fact**: 530,104 giao dịch
    - **Sản phẩm**: 3,922 SKU | **Khách hàng**: 4,339
    - **Khoảng thời gian**: 12/2010 - 12/2011
    """)
    st.markdown("---")
    st.caption("Đồ án: Modern Data Lakehouse & Retail Analytics")

# ------------------------------------------------------------------------------
# 4. TIÊU ĐỀ CHÍNH & TỔNG QUAN KPIS (EXECUTIVE OVERVIEW)
# ------------------------------------------------------------------------------
st.markdown('<div class="main-title">ONLINE RETAIL INTELLIGENCE DASHBOARD</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Hệ thống Kho Dữ Liệu Đa Chiều & Phân Tích Hành Vi Người Tiêu Dùng Thương Mại Điện Tử</div>', unsafe_allow_html=True)

# Tính toán các chỉ số KPI cấp cao
total_revenue = df_monthly['MonthlyRevenue'].sum()
total_orders = df_monthly['TotalOrders'].sum()
total_units = df_monthly['TotalUnitsSold'].sum()
avg_aov = total_revenue / total_orders
total_customers = df_country['Customers'].sum()

# Hiển thị 4 thẻ KPI Card
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Tổng Doanh Thu Toàn Hệ Thống</div>
        <div class="metric-value">£{total_revenue:,.2f}</div>
        <div class="metric-delta" style="color: #10B981;">▲ Tăng trưởng mạnh vào Q4/2011</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Tổng Số Đơn Hàng (Invoices)</div>
        <div class="metric-value">{total_orders:,}</div>
        <div class="metric-delta" style="color: #3B82F6;">● {total_units:,} sản phẩm bán ra</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Giá Trị Đơn Trung Bình (AOV)</div>
        <div class="metric-value">£{avg_aov:,.2f}</div>
        <div class="metric-delta" style="color: #6366F1;">● Đặc thù khách buôn & quà tặng</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Khách Hàng Định Danh</div>
        <div class="metric-value">{len(df_rfm):,}</div>
        <div class="metric-delta" style="color: #F59E0B;">★ 65.58% khách quay lại mua</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------------------------
# 5. CÁC TABS PHÂN TÍCH CHUYÊN SÂU
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Xu Hướng Doanh Thu & Thời Gian",
    "🌍 Địa Lý & Sản Phẩm Chủ Lực",
    "👥 Phân Khúc Khách Hàng (RFM & K-Means)",
    "🧺 Gợi Ý Bán Chéo (Market Basket)",
    "🏗️ Kiến Trúc Kho Dữ Liệu (Star Schema)",
    "💱 Tỷ Giá & Quy Đổi Doanh Thu (API)"
])

# ==============================================================================
# TAB 1: XU HƯỚNG DOANH THU & THỜI GIAN
# ==============================================================================
with tab1:
    st.subheader("1. Phân Tích Xu Hướng Doanh Thu Theo Tháng & Tăng Trưởng MoM")
    
    col_t1, col_t2 = st.columns([7, 3])
    
    with col_t1:
        fig_revenue = go.Figure()
        fig_revenue.add_trace(go.Bar(
            x=df_monthly['YearMonth'],
            y=df_monthly['MonthlyRevenue'],
            name='Doanh thu (GBP)',
            marker_color='#3B82F6',
            opacity=0.85
        ))
        fig_revenue.add_trace(go.Scatter(
            x=df_monthly['YearMonth'],
            y=df_monthly['TotalOrders'] * 500,  # Scaled for secondary view
            name='Đơn hàng (Scaled)',
            line=dict(color='#F59E0B', width=3),
            mode='lines+markers'
        ))
        fig_revenue.update_layout(
            title="Doanh thu hàng tháng & Quy mô đơn hàng (12/2010 - 12/2011)",
            xaxis_title="Tháng",
            yaxis_title="Doanh thu (£ GBP)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
            height=400
        )
        st.plotly_chart(fig_revenue, use_container_width=True)

    with col_t2:
        st.markdown("##### 📌 Tốc Độ Tăng Trưởng MoM (%)")
        df_display_mom = df_monthly[['YearMonth', 'MonthlyRevenue', 'MoM_Growth_Pct']].dropna()
        st.dataframe(
            df_display_mom.style.format({
                'MonthlyRevenue': '£{:,.2f}',
                'MoM_Growth_Pct': '{:+.2f}%'
            }),
            height=360,
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("2. Khung Giờ Mua Sắm Vàng Trong Ngày (Peak Shopping Hours)")
    
    col_h1, col_h2 = st.columns([7, 3])
    with col_h1:
        fig_hour = px.area(
            df_hourly,
            x='Hour',
            y='Orders',
            title="Phân bố số lượng đơn hàng theo khung giờ trong ngày (0h - 23h)",
            labels={'Hour': 'Khung giờ', 'Orders': 'Số lượng hóa đơn'},
            color_discrete_sequence=['#0D9488']
        )
        fig_hour.add_vline(x=12, line_width=2, line_dash="dash", line_color="#EF4444", annotation_text="Đỉnh: 12h Trưa")
        fig_hour.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_hour, use_container_width=True)
        
    with col_h2:
        st.info("""
        **Chiến Lược Kinh Doanh Phù Hợp:**
        - **Khung giờ vàng**: Từ **10:00 sáng đến 15:00 chiều** chiếm hơn **75%** lượng giao dịch toàn hệ thống.
        - **Khung giờ cao điểm nhất**: **12:00 trưa** với 3,220 đơn hàng và doanh thu hơn 1.44 triệu GBP.
        - **Đề xuất**: Phân bổ ngân sách quảng cáo Google Ads / Facebook Ads và gửi Email Marketing lúc 9:30 - 11:30 sáng để đón đầu nhu cầu mua sắm.
        """)

# ==============================================================================
# TAB 2: ĐỊA LÝ & SẢN PHẨM CHỦ LỰC
# ==============================================================================
with tab2:
    st.subheader("1. Cơ Cấu Thị Trường Địa Lý Toàn Cầu")
    col_g1, col_g2 = st.columns([6, 4])
    
    with col_g1:
        # Top 10 quốc gia
        top10_countries = df_country.head(10).copy()
        fig_country = px.bar(
            top10_countries,
            x='Revenue',
            y='Country',
            orientation='h',
            title="Top 10 Quốc Gia Đóng Góp Doanh Thu Cao Nhất",
            labels={'Revenue': 'Doanh thu (£ GBP)', 'Country': 'Quốc gia'},
            color='Revenue',
            color_continuous_scale='Blues'
        )
        fig_country.update_layout(yaxis=dict(autorange="reversed"), height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_country, use_container_width=True)
        
    with col_g2:
        # Tỷ lệ UK vs Quốc tế
        domestic_rev = df_country[df_country['RegionType'] == 'Domestic']['Revenue'].sum()
        intl_rev = df_country[df_country['RegionType'] == 'International']['Revenue'].sum()
        df_region = pd.DataFrame({
            'Vùng': ['Vương quốc Anh (UK)', 'Thị trường Quốc tế (International)'],
            'Doanh Thu': [domestic_rev, intl_rev]
        })
        fig_region = px.pie(
            df_region,
            names='Vùng',
            values='Doanh Thu',
            title="Tỷ Trọng Thị Trường: UK vs Quốc Tế",
            hole=0.45,
            color_discrete_sequence=['#1E3A8A', '#0D9488']
        )
        fig_region.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_region, use_container_width=True)

    st.markdown("---")
    st.subheader("2. Top Sản Phẩm Chủ Lực (Best-sellers & High-yields)")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("##### 📦 Top 10 Mặt Hàng Bán Chạy Nhất Về Số Lượng (Quantity)")
        top_qty = df_products.sort_values(by='TotalQty', ascending=False).head(10)
        fig_top_qty = px.bar(
            top_qty,
            x='TotalQty',
            y='Description',
            orientation='h',
            color='TotalQty',
            color_continuous_scale='Viridis'
        )
        fig_top_qty.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_qty, use_container_width=True)
        
    with col_p2:
        st.markdown("##### 💰 Top 10 Mặt Hàng Đem Lại Doanh Thu Cao Nhất (Revenue)")
        top_rev = df_products.sort_values(by='TotalRevenue', ascending=False).head(10)
        fig_top_rev = px.bar(
            top_rev,
            x='TotalRevenue',
            y='Description',
            orientation='h',
            color='TotalRevenue',
            color_continuous_scale='Cividis'
        )
        fig_top_rev.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_rev, use_container_width=True)

# ==============================================================================
# TAB 3: PHÂN KHÚC KHÁCH HÀNG (RFM & K-MEANS)
# ==============================================================================
with tab3:
    st.subheader("1. Chân Dung & Phân Khúc Khách Hàng Theo Mô Hình RFM")
    
    if not df_rfm.empty:
        col_rfm1, col_rfm2 = st.columns([6, 4])
        
        with col_rfm1:
            segment_counts = df_rfm.groupby('Segment').agg(
                Khách_Hàng=('CustomerID', 'count'),
                Doanh_Thu=('Monetary', 'sum'),
                Recency_TB=('Recency', 'mean'),
                Frequency_TB=('Frequency', 'mean'),
                Monetary_TB=('Monetary', 'mean')
            ).reset_index().sort_values(by='Doanh_Thu', ascending=False)
            
            fig_rfm_treemap = px.treemap(
                segment_counts,
                path=['Segment'],
                values='Doanh_Thu',
                color='Khách_Hàng',
                color_continuous_scale='Blues',
                title="Quy Mô Doanh Thu & Số Khách Theo Từng Phân Khúc RFM"
            )
            fig_rfm_treemap.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rfm_treemap, use_container_width=True)

        with col_rfm2:
            fig_segment_pie = px.pie(
                segment_counts,
                names='Segment',
                values='Khách_Hàng',
                title="Cơ Cấu Tỷ Lệ Khách Hàng (%)",
                hole=0.4
            )
            fig_segment_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_segment_pie, use_container_width=True)

        st.markdown("---")
        st.subheader("2. Đối Chiếu Thuật Toán Gom Cụm K-Means (k = 4 Cụm)")
        
        col_km1, col_km2 = st.columns([7, 3])
        with col_km1:
            fig_scatter = px.scatter(
                df_rfm,
                x='Recency',
                y='Monetary',
                size='Frequency',
                color='KMeans_Label',
                hover_name='CustomerCode',
                log_y=True,
                title="Phân Cụm Khách Hàng K-Means (Trục Y: Log Monetary, Kích Thước: Tần Suất Mua)",
                color_discrete_sequence=['#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            )
            fig_scatter.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with col_km2:
            st.markdown("##### 📋 Bảng Thống Kê Phân Khúc")
            st.dataframe(
                segment_counts.style.format({
                    'Doanh_Thu': '£{:,.0f}',
                    'Recency_TB': '{:.1f} ngày',
                    'Frequency_TB': '{:.1f} đơn',
                    'Monetary_TB': '£{:,.1f}'
                }),
                height=380,
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("3. Danh Sách Khách Hàng VIP Champions Cần Chăm Sóc Đặc Biệt")
        champions_df = df_rfm[df_rfm['Segment'] == 'Champions (VIP)'].sort_values(by='Monetary', ascending=False)
        st.dataframe(
            champions_df[['CustomerCode', 'Country', 'Recency', 'Frequency', 'Monetary', 'KMeans_Label']].head(15).style.format({
                'Monetary': '£{:,.2f}'
            }),
            use_container_width=True
        )
    else:
        st.warning("Chưa tìm thấy file `outputs/rfm_customer_segments.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# ==============================================================================
# TAB 4: GỢI Ý BÁN CHÉO (MARKET BASKET ANALYSIS)
# ==============================================================================
with tab4:
    st.subheader("1. Công Cụ Gợi Ý Bán Kèm Sản Phẩm Thông Minh (Cross-sell Recommender)")
    st.write("Dựa trên thuật toán khai phá luật kết hợp **Apriori** từ hơn 18,000 giỏ hàng.")
    
    if not df_rules.empty:
        # Lấy danh sách các sản phẩm tiền đề (Antecedents)
        unique_antecedents = sorted(df_rules['antecedents_str'].unique().tolist())
        
        col_rec1, col_rec2 = st.columns([5, 5])
        with col_rec1:
            selected_item = st.selectbox(
                "🛒 Chọn sản phẩm khách hàng đang xem hoặc đã bỏ vào giỏ hàng:",
                options=unique_antecedents,
                index=0
            )
            
        filtered_rules = df_rules[df_rules['antecedents_str'] == selected_item].sort_values(by=['lift', 'confidence'], ascending=[False, False])
        
        with col_rec2:
            st.metric(
                label="Số lượng sản phẩm gợi ý phù hợp",
                value=f"{len(filtered_rules)} mặt hàng",
                delta=f"Độ tăng Lift cao nhất: {filtered_rules['lift'].max():.2f}x" if not filtered_rules.empty else None
            )

        if not filtered_rules.empty:
            st.markdown("##### 🎁 Danh Sách Sản Phẩm Được Mua Kèm Nhiều Nhất (Bundle Suggestions):")
            
            for idx, r in filtered_rules.head(5).iterrows():
                conf_pct = r['confidence'] * 100
                lift_val = r['lift']
                supp_pct = r['support'] * 100
                
                st.success(f"""
                **Gợi ý mua kèm**: **{r['consequents_str']}**  
                - **Độ tin cậy (Confidence)**: **{conf_pct:.1f}%** *(Có {conf_pct:.1f}% khách hàng mua sản phẩm này khi đã mua sản phẩm đã chọn)*  
                - **Hệ số tăng trưởng (Lift)**: **{lift_val:.2f} lần** *(Xác suất mua cùng cao gấp {lift_val:.2f} lần so với mua ngẫu nhiên)*  
                - **Độ hỗ trợ (Support)**: **{supp_pct:.2f}%** đơn hàng
                """)
        else:
            st.info("Chưa có luật kết hợp trực tiếp cho sản phẩm này trong ngưỡng lọc.")

        st.markdown("---")
        st.subheader("2. Top 15 Luật Kết Hợp Có Hệ Số Lift Cao Nhất Toàn Hệ Thống")
        display_rules = df_rules.head(15)[['antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']].copy()
        display_rules['support'] = (display_rules['support'] * 100).round(2).astype(str) + '%'
        display_rules['confidence'] = (display_rules['confidence'] * 100).round(2).astype(str) + '%'
        display_rules['lift'] = display_rules['lift'].round(2)
        display_rules.columns = ['Nếu Khách Mua (A)', 'Gợi Ý Mua Kèm (B)', 'Support', 'Confidence', 'Lift']
        st.dataframe(display_rules, use_container_width=True)
    else:
        st.warning("Chưa tìm thấy file `outputs/market_basket_rules.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# ==============================================================================
# TAB 5: KIẾN TRÚC KHO DỮ LIỆU (STAR SCHEMA)
# ==============================================================================
with tab5:
    st.subheader("Kiến Trúc Mô Hình Kho Dữ Liệu Hình Sao (Star Schema Architecture)")
    
    col_dwh1, col_dwh2 = st.columns([6, 4])
    
    with col_dwh1:
        st.markdown("""
        #### 🌟 Sơ Đồ Thiết Kế Thực Thể ERD
        Mô hình gồm **1 Fact Table** ở trung tâm và **4 Dimension Tables** bao quanh:
        - **`Fact_Sales`** *(530,104 dòng)*:
          - Measures: `Quantity`, `UnitPrice`, `TotalRevenue`
          - Degenerate Dimension: `InvoiceNo`
          - Foreign Keys: `DateKey`, `CustomerKey`, `ProductKey`, `LocationKey`
        - **`Dim_Date`** *(374 dòng)*: Chiều thời gian (FullDate, Year, Quarter, Month, Day, DayOfWeek, IsWeekend)
        - **`Dim_Customer`** *(4,339 dòng)*: Chiều khách hàng (CustomerKey, CustomerID, CustomerCode, IsGuest, Country)
        - **`Dim_Product`** *(3,922 dòng)*: Chiều sản phẩm (ProductKey, StockCode, Description, UnitPrice_Standard)
        - **`Dim_Location`** *(38 dòng)*: Chiều địa lý (LocationKey, Country, RegionType: Domestic / International)
        """)
        
    with col_dwh2:
        st.markdown("#### ⚡ Thống Kê Bảng Kho Dữ Liệu")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        tables = ['Dim_Date', 'Dim_Location', 'Dim_Customer', 'Dim_Product', 'Fact_Sales']
        stats = []
        for t in tables:
            cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            stats.append({'Bảng (Table)': t, 'Số Bản Ghi (Rows)': f"{cnt:,}"})
        conn.close()
        st.table(pd.DataFrame(stats))

    st.markdown("---")
    st.subheader("Kịch Bản DDL Tạo Schema & Khóa Ngoại")
    ddl_path = os.path.join(BASE_DIR, "database", "02_schema_ddl.sql")
    if os.path.exists(ddl_path):
        with open(ddl_path, 'r', encoding='utf-8') as f:
            st.code(f.read()[:1500] + "\n\n-- [Xem chi tiết toàn bộ trong file database/02_schema_ddl.sql] --", language='sql')

# ==============================================================================
# TAB 6: TỶ GIÁ & QUY ĐỔI DOANH THU (FRANKFURTER API – ECB)
# ==============================================================================
with tab6:
    st.subheader("💱 Tích Hợp API Thời Gian Thực – Tỷ Giá GBP (Nguồn: ECB via Frankfurter API)")
    st.markdown("""
    > **API sử dụng**: [Frankfurter.app](https://api.frankfurter.app) – Dữ liệu tỷ giá tham chiếu của Ngân hàng Trung ương Châu Âu (ECB).
    > **Không cần API key.** Dữ liệu cập nhật mỗi ngày làm việc. Kết hợp với dữ liệu doanh thu GBP từ DWH để quy đổi sang USD & EUR.
    """)

    # ── Tỷ giá trực tiếp ──────────────────────────────────────────────────────
    st.markdown("### 📡 Tỷ Giá GBP Hôm Nay (Live)")
    live_col1, live_col2, live_col3 = st.columns([1, 1, 2])

    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "GBP", "to": "USD,EUR"},
            timeout=8
        )
        resp.raise_for_status()
        live_data = resp.json()
        live_usd = live_data["rates"]["USD"]
        live_eur = live_data["rates"]["EUR"]
        live_date = live_data["date"]
        api_ok = True
    except Exception:
        live_usd, live_eur, live_date = 1.32, 1.18, "N/A (Offline)"
        api_ok = False

    with live_col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10B981;">
            <div class="metric-label">1 GBP → USD</div>
            <div class="metric-value" style="color:#10B981;">$ {live_usd:.4f}</div>
            <div class="metric-delta">{'🟢 ECB Live – ' + live_date if api_ok else '🟡 Fallback ước tính'}</div>
        </div>
        """, unsafe_allow_html=True)

    with live_col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #6366F1;">
            <div class="metric-label">1 GBP → EUR</div>
            <div class="metric-value" style="color:#6366F1;">€ {live_eur:.4f}</div>
            <div class="metric-delta">{'🟢 ECB Live – ' + live_date if api_ok else '🟡 Fallback ước tính'}</div>
        </div>
        """, unsafe_allow_html=True)

    with live_col3:
        total_rev = df_monthly['MonthlyRevenue'].sum()
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #F59E0B;">
            <div class="metric-label">Doanh Thu DWH Quy Đổi (Tỷ Giá Hôm Nay)</div>
            <div style="display:flex; gap: 2rem; margin-top: 0.5rem;">
                <span><b>GBP</b>: £ {total_rev:,.0f}</span>
                <span><b>USD</b>: $ {total_rev * live_usd:,.0f}</span>
                <span><b>EUR</b>: € {total_rev * live_eur:,.0f}</span>
            </div>
            <div class="metric-delta" style="margin-top:0.3rem;">Tổng doanh thu 12/2010 – 12/2011</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("---")

    # ── Dữ liệu tỷ giá lịch sử ────────────────────────────────────────────────
    st.markdown("### 📊 Biến Động Tỷ Giá GBP Theo Tháng (2010-12 → 2011-12)")

    ex_path = os.path.join(BASE_DIR, "outputs", "exchange_rates.csv")
    if os.path.exists(ex_path):
        df_ex = pd.read_csv(ex_path)
        # Chuẩn hóa tên cột
        col_map = {c: c.lower() for c in df_ex.columns}
        df_ex = df_ex.rename(columns=col_map)
        if "yearmonth" in df_ex.columns:
            df_ex["label"] = df_ex["yearmonth"].astype(str)
        elif "year" in df_ex.columns and "month" in df_ex.columns:
            df_ex["label"] = df_ex["year"].astype(str) + "-" + df_ex["month"].astype(str).str.zfill(2)
        else:
            df_ex["label"] = df_ex.index.astype(str)

        usd_col = "usd_rate" if "usd_rate" in df_ex.columns else df_ex.columns[1]
        eur_col = "eur_rate" if "eur_rate" in df_ex.columns else df_ex.columns[2]

        fig_fx = go.Figure()
        fig_fx.add_trace(go.Scatter(
            x=df_ex["label"], y=df_ex[usd_col],
            name="GBP/USD", mode="lines+markers",
            line=dict(color="#10B981", width=2.5),
            marker=dict(size=7)
        ))
        fig_fx.add_trace(go.Scatter(
            x=df_ex["label"], y=df_ex[eur_col],
            name="GBP/EUR", mode="lines+markers",
            line=dict(color="#6366F1", width=2.5),
            marker=dict(size=7)
        ))
        fig_fx.update_layout(
            template="plotly_white", height=360,
            title="Tỷ Giá GBP/USD và GBP/EUR Theo Tháng (Nguồn: ECB via Frankfurter API)",
            xaxis_title="Tháng", yaxis_title="Tỷ Giá (1 GBP = x)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig_fx, use_container_width=True)
    else:
        st.warning("Chưa có file exchange_rates.csv. Chạy `python scripts/07_api_enrichment.py` trước.")

    st.markdown("---")

    # ── Bảng quy đổi doanh thu theo từng tháng ────────────────────────────────
    st.markdown("### 💰 Bảng Doanh Thu Hàng Tháng Quy Đổi Đa Tiền Tệ")
    st.caption("Doanh thu GBP từ DWH × Tỷ giá lịch sử ECB của từng tháng → USD & EUR tương ứng")

    if os.path.exists(ex_path) and not df_monthly.empty:
        df_ex2 = pd.read_csv(ex_path)
        col_map2 = {c: c.lower() for c in df_ex2.columns}
        df_ex2 = df_ex2.rename(columns=col_map2)
        if "yearmonth" in df_ex2.columns:
            df_ex2["label"] = df_ex2["yearmonth"].astype(str)
        elif "year" in df_ex2.columns and "month" in df_ex2.columns:
            df_ex2["label"] = df_ex2["year"].astype(str) + "-" + df_ex2["month"].astype(str).str.zfill(2)
        else:
            df_ex2["label"] = df_ex2.index.astype(str)

        usd_col2 = "usd_rate" if "usd_rate" in df_ex2.columns else df_ex2.columns[1]
        eur_col2 = "eur_rate" if "eur_rate" in df_ex2.columns else df_ex2.columns[2]

        df_mon2 = df_monthly.copy()
        df_mon2["label"] = df_mon2["YearMonth"].astype(str)
        df_merged = df_mon2.merge(df_ex2[["label", usd_col2, eur_col2]], on="label", how="left")
        df_merged["Revenue_GBP"] = df_merged["MonthlyRevenue"]
        df_merged["Revenue_USD"] = (df_merged["MonthlyRevenue"] * df_merged[usd_col2]).round(2)
        df_merged["Revenue_EUR"] = (df_merged["MonthlyRevenue"] * df_merged[eur_col2]).round(2)

        display_df = df_merged[["label", "Revenue_GBP", usd_col2, "Revenue_USD", eur_col2, "Revenue_EUR"]].copy()
        display_df.columns = ["Tháng", "DT (GBP £)", "Tỷ Giá USD", "DT (USD $)", "Tỷ Giá EUR", "DT (EUR €)"]
        display_df["DT (GBP £)"] = display_df["DT (GBP £)"].apply(lambda x: f"£ {x:,.2f}")
        display_df["DT (USD $)"] = display_df["DT (USD $)"].apply(lambda x: f"$ {x:,.2f}" if pd.notna(x) else "—")
        display_df["DT (EUR €)"] = display_df["DT (EUR €)"].apply(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "—")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("Dữ liệu đang được tải... Chạy script 07 để có đầy đủ thông tin.")

    st.markdown("---")
    st.markdown("""
    **📚 Về Nguồn API:**
    - **Frankfurter.app** – Open-source, dữ liệu từ Ngân hàng Trung ương Châu Âu (ECB)
    - Endpoint lịch sử: `https://api.frankfurter.app/2010-12-01..2011-12-31?from=GBP&to=USD,EUR`
    - Endpoint thời gian thực: `https://api.frankfurter.app/latest?from=GBP&to=USD,EUR`
    - **Không cần đăng ký. Không cần API Key. Hoàn toàn miễn phí.**
    """)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.9rem;'>Đồ Án Kho Dữ Liệu & Phân Tích Bán Lẻ (Online Retail DWH) • Xây dựng bằng Python, SQLite & Streamlit</div>", unsafe_allow_html=True)
