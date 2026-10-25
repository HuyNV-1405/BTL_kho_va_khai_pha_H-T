"""
File: 01_eda_and_cleaning.py
Mô tả: Khám phá chất lượng dữ liệu (EDA), phân tích độ hạt giao dịch, kiểm tra trùng lặp,
       phân loại lý do loại trừ dữ liệu và tiền xử lý làm sạch chuẩn hóa phục vụ DWH & Data Mining.
"""

import os
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "data.csv")
CLEAN_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
REJECTED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_rejected.csv")
AUDIT_OUTPUT_PATH = os.path.join(BASE_DIR, "outputs", "data_cleaning_audit.csv")

os.makedirs(os.path.join(BASE_DIR, "data", "processed"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)

def run_eda_and_cleaning(
    input_file=None, 
    output_clean=None,
    output_rejected=None,
    output_audit=None
):
    if input_file is None:
        input_file = RAW_DATA_PATH
    if output_clean is None:
        output_clean = CLEAN_DATA_PATH
    if output_rejected is None:
        output_rejected = REJECTED_DATA_PATH
    if output_audit is None:
        output_audit = AUDIT_OUTPUT_PATH

    print("=" * 85)
    print(" GIAI ĐOẠN 1: KHÁM PHÁ CHẤT LƯỢNG DỮ LIỆU (EDA) & XÂY DỰNG QUY TẮC LÀM SẠCH")
    print("=" * 85)

    # --------------------------------------------------------------------------
    # 1. ĐỌC DỮ LIỆU & KIỂM TRA ĐỘ HẠT (GRANULARITY & SCHEMA VERIFICATION)
    # --------------------------------------------------------------------------
    print(f"\n[BƯỚC 1/6] ĐỌC DỮ LIỆU & XÁC NHẬN ĐỘ HẠT TỪ '{input_file}'...")
    # BẢO TOÀN KIỂU CHUỖI cho InvoiceNo và StockCode (tránh mất số 0 đầu hoặc ký tự chữ cái)
    dtype_spec = {
        'InvoiceNo': str,
        'StockCode': str,
        'Description': str,
        'Country': str
    }
    try:
        df = pd.read_csv(input_file, encoding='utf-8', dtype=dtype_spec)
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, encoding='ISO-8859-1', dtype=dtype_spec)

    total_raw_rows = len(df)
    print(f"-> Quy mô dữ liệu ban đầu: {total_raw_rows:,} dòng x {len(df.columns)} cột.")
    
    required_cols = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        raise ValueError(f"Dữ liệu thiếu các cột bắt buộc cho DWH: {missing_required}")
    print(f"-> Kiểm tra trường bắt buộc: Đầy đủ cả 8/8 cột ({', '.join(required_cols)}) [OK]")
    print("-> Độ hạt giao dịch (Granularity): 1 dòng = 1 mặt hàng trong 1 hóa đơn (Line-item level).")

    # --------------------------------------------------------------------------
    # 2. KHẢO SÁT CHẤT LƯỢNG DỮ LIỆU NGUỒN & XỬ LÝ KHUYẾT THIẾU
    # --------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print("[BƯỚC 2/6] KHẢO SÁT CHẤT LƯỢNG DỮ LIỆU NGUỒN (MISSING, DUPLICATES, ANOMALIES)")
    print("=" * 85)

    # 2.1 Missing Values
    null_counts = df.isnull().sum()
    null_pct = (null_counts / total_raw_rows) * 100
    missing_df = pd.DataFrame({"Missing_Count": null_counts, "Percentage(%)": null_pct.round(2)})
    print("\n1. Thống kê dữ liệu khuyết thiếu (Missing Values):")
    print(missing_df[missing_df["Missing_Count"] > 0])

    # Chuẩn hóa chuỗi InvoiceNo và StockCode
    df['InvoiceNo'] = df['InvoiceNo'].astype(str).str.strip()
    df['StockCode'] = df['StockCode'].astype(str).str.strip()

    # Kiểm tra tính hợp lệ của StockCode và InvoiceDate
    invalid_stockcode = (df['StockCode'].isnull()) | (df['StockCode'] == '') | (df['StockCode'].str.lower() == 'nan')
    parsed_dates = pd.to_datetime(df['InvoiceDate'], errors='coerce')
    invalid_date = parsed_dates.isnull()
    parsed_qty = pd.to_numeric(df['Quantity'], errors='coerce')
    invalid_qty = parsed_qty.isnull()
    parsed_price = pd.to_numeric(df['UnitPrice'], errors='coerce')
    invalid_price = parsed_price.isnull()

    print(f"\n2. Kiểm tra tính toàn vẹn định dạng kỹ thuật:")
    print(f"   + StockCode bị rỗng / không hợp lệ: {invalid_stockcode.sum():,} dòng")
    print(f"   + InvoiceDate không parse được: {invalid_date.sum():,} dòng")
    print(f"   + Quantity không phải số: {invalid_qty.sum():,} dòng")
    print(f"   + UnitPrice không phải số: {invalid_price.sum():,} dòng")

    # 2.2 Xử lý Description: Bổ sung từ StockCode (Imputation) thay vì tự động ép thành 'NAN'
    print(f"\n3. Phân tích cột Description & Ánh xạ khôi phục:")
    # Nhận diện dòng thiếu Description thực sự (bao gồm null, rỗng, hoặc chuỗi 'nan')
    is_raw_desc_missing = df['Description'].isnull() | (df['Description'].astype(str).str.strip() == '') | (df['Description'].astype(str).str.lower() == 'nan')
    raw_missing_desc_count = is_raw_desc_missing.sum()
    print(f"   + Tổng số dòng thiếu Description ban đầu: {raw_missing_desc_count:,} dòng ({raw_missing_desc_count/total_raw_rows*100:.2f}%)")

    # Xây dựng từ điển tra cứu StockCode -> Description từ các bản ghi hợp lệ
    valid_desc_df = df[~is_raw_desc_missing].copy()
    valid_desc_df['CleanDesc'] = valid_desc_df['Description'].astype(str).str.strip().str.upper()
    stock_desc_lookup = valid_desc_df.groupby('StockCode')['CleanDesc'].agg(
        lambda s: s.mode().iloc[0] if not s.empty else np.nan
    ).to_dict()

    # Bổ sung Description từ StockCode
    imputed_desc_series = df['StockCode'].map(stock_desc_lookup)
    can_impute_count = (is_raw_desc_missing & imputed_desc_series.notnull()).sum()
    cannot_impute_count = (is_raw_desc_missing & imputed_desc_series.isnull()).sum()
    print(f"   + Số dòng khôi phục được Description từ StockCode: {can_impute_count:,} dòng")
    print(f"   + Số dòng hoàn toàn không có ánh xạ Description: {cannot_impute_count:,} dòng (Toàn bộ có UnitPrice = 0.00)")

    # Gán mô tả đã khôi phục vào DataFrame làm việc
    df['Description_Clean'] = df['Description'].where(~is_raw_desc_missing, imputed_desc_series)
    df['Description_Clean'] = df['Description_Clean'].fillna('UNKNOWN DESCRIPTION').astype(str).str.strip().str.upper()

    # 2.3 Phân tích bản ghi trùng lặp
    exact_dups = df.duplicated()
    exact_dup_count = exact_dups.sum()
    pair_dups = df.duplicated(subset=['InvoiceNo', 'StockCode'], keep=False)
    print(f"\n4. Thống kê bản ghi trùng lặp:")
    print(f"   + Trùng lặp tuyệt đối (100% các cột): {exact_dup_count:,} dòng ({exact_dup_count/total_raw_rows*100:.2f}%)")
    print(f"   + Dòng có cùng (InvoiceNo, StockCode) nhưng khác số lượng/đơn giá: {pair_dups.sum() - exact_dup_count:,} dòng")
    print("   -> QUY TẮC: CHỈ loại bỏ các bản ghi trùng lặp 100% (do lỗi duplicate nạp kép).")
    print("      Các dòng có cùng sản phẩm trong một hóa đơn nhưng có số lượng khác nhau được GIỮ NGUYÊN (mua theo đợt hợp lệ).")

    # --------------------------------------------------------------------------
    # 3. QUY TRÌNH PHÂN LOẠI & GẮN NHÃN DÒNG BỊ LOẠI (WATERFALL AUDIT & REJECTION)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print("[BƯỚC 3/6] THỰC THI QUY TẮC LÀM SẠCH & PHÂN LOẠI DÒNG BỊ LOẠI (WATERFALL)")
    print("=" * 85)

    df_work = df.copy()
    # Tính GrossAmount ban đầu để kiểm toán doanh thu
    df_work['Quantity_Clean'] = pd.to_numeric(df_work['Quantity'], errors='coerce').fillna(0)
    df_work['UnitPrice_Clean'] = pd.to_numeric(df_work['UnitPrice'], errors='coerce').fillna(0.0)
    df_work['GrossAmount'] = (df_work['Quantity_Clean'] * df_work['UnitPrice_Clean']).round(2)
    
    # Định nghĩa các điều kiện theo thứ tự ưu tiên (Priority Waterfall)
    # 1. Trùng lặp tuyệt đối
    is_exact_dup = df_work.duplicated(keep='first')
    
    # 2. Hóa đơn hủy (InvoiceNo bắt đầu bằng 'C')
    is_cancelled = (~is_exact_dup) & df_work['InvoiceNo'].str.startswith('C')
    
    # 3. Số lượng không dương (hàng trả, hư hỏng, kiểm kê)
    is_neg_qty = (~is_exact_dup) & (~is_cancelled) & (df_work['Quantity_Clean'] <= 0)
    
    # 4. Đơn giá không dương hoặc làm tròn thành 0.00 (quà tặng, hàng thử mẫu, lỗi kỹ thuật kiểm kê, phí giả lập 0.001)
    is_neg_price = (~is_exact_dup) & (~is_cancelled) & (~is_neg_qty) & (df_work['UnitPrice_Clean'].round(2) <= 0)

    # 5. Lỗi kỹ thuật khác (nếu có: ngày rỗng, mã rỗng)
    is_invalid_tech = (~is_exact_dup) & (~is_cancelled) & (~is_neg_qty) & (~is_neg_price) & (invalid_stockcode | invalid_date)

    # Gán nhãn lý do loại rõ ràng
    rejection_reason = pd.Series(index=df_work.index, dtype='object')
    rejection_reason[is_exact_dup] = 'EXACT_DUPLICATE'
    rejection_reason[is_cancelled] = 'CANCELLED_INVOICE'
    rejection_reason[is_neg_qty] = 'NON_POSITIVE_QUANTITY'
    rejection_reason[is_neg_price] = 'NON_POSITIVE_UNITPRICE'
    rejection_reason[is_invalid_tech] = 'INVALID_TECHNICAL_FORMAT'

    rejected_mask = is_exact_dup | is_cancelled | is_neg_qty | is_neg_price | is_invalid_tech
    df_rejected = df_work[rejected_mask].copy()
    df_rejected['RejectReason'] = rejection_reason[rejected_mask]

    # Lưu tập dữ liệu bị loại
    print(f"-> Đang lưu {len(df_rejected):,} dòng bị loại vào '{output_rejected}'...")
    cols_rejected = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country', 'GrossAmount', 'RejectReason']
    df_rejected[cols_rejected].to_csv(output_rejected, index=False)
    print("-> Đã lưu thành công dữ liệu bị loại có gắn nhãn lý do chi tiết [OK]")

    # Lập bảng đối soát Waterfall Audit
    audit_steps = [
        ("1. Tổng dữ liệu thô ban đầu (Raw Data)", total_raw_rows, df_work['InvoiceNo'].nunique(), df_work['GrossAmount'].sum()),
        ("2. Loại bản ghi trùng lặp tuyệt đối (Exact Duplicates)", is_exact_dup.sum(), df_work.loc[is_exact_dup, 'InvoiceNo'].nunique(), df_work.loc[is_exact_dup, 'GrossAmount'].sum()),
        ("3. Loại hóa đơn hủy bỏ (Cancelled Invoices)", is_cancelled.sum(), df_work.loc[is_cancelled, 'InvoiceNo'].nunique(), df_work.loc[is_cancelled, 'GrossAmount'].sum()),
        ("4. Loại số lượng <= 0 (Non-positive Quantity)", is_neg_qty.sum(), df_work.loc[is_neg_qty, 'InvoiceNo'].nunique(), df_work.loc[is_neg_qty, 'GrossAmount'].sum()),
        ("5. Loại đơn giá <= 0 (Non-positive UnitPrice)", is_neg_price.sum(), df_work.loc[is_neg_price, 'InvoiceNo'].nunique(), df_work.loc[is_neg_price, 'GrossAmount'].sum()),
        ("6. TẬP DỮ LIỆU SẠCH CUỐI CÙNG (CLEAN DATA)", (~rejected_mask).sum(), df_work.loc[~rejected_mask, 'InvoiceNo'].nunique(), df_work.loc[~rejected_mask, 'GrossAmount'].sum())
    ]
    
    df_audit = pd.DataFrame(audit_steps, columns=["Bước kiểm tra / Quy tắc", "Số dòng", "Số hóa đơn", "Tổng doanh thu (GBP)"])
    df_audit["Tỷ lệ dòng (%)"] = (df_audit["Số dòng"] / total_raw_rows * 100).round(2)
    print("\nBảng đối soát Waterfall qua từng quy tắc làm sạch:")
    print(df_audit.to_string(index=False))

    df_audit.to_csv(output_audit, index=False)
    print(f"-> Đã lưu báo cáo đối soát làm sạch vào '{output_audit}' [OK]")

    # --------------------------------------------------------------------------
    # 4. CHUẨN HÓA DỮ LIỆU SẠCH (TRANSFORMATION & ENRICHMENT)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print("[BƯỚC 4/6] CHUẨN HÓA DỮ LIỆU SẠCH & THỐNG NHẤT CÔNG THỨC DOANH THU")
    print("=" * 85)

    df_clean = df_work[~rejected_mask].copy()

    # 4.1 Description và StockCode sạch
    df_clean['Description'] = df_clean['Description_Clean']
    print(f"-> Kiểm tra Description trong tập sạch: 100% hợp lệ, không có chuỗi 'NAN' rác.")

    # 4.2 Chuẩn hóa InvoiceDate
    df_clean['InvoiceDate'] = pd.to_datetime(df_clean['InvoiceDate'])
    print(f"-> Chuẩn hóa InvoiceDate: Từ {df_clean['InvoiceDate'].min()} đến {df_clean['InvoiceDate'].max()} [OK]")

    # 4.3 Xử lý CustomerID: Tách bạch khách vãng lai
    df_clean['IsGuestCustomer'] = df_clean['CustomerID'].isnull().astype(int)
    df_clean['CustomerID_Clean'] = df_clean['CustomerID'].fillna(-1).astype(int)
    guest_count = df_clean['IsGuestCustomer'].sum()
    identified_count = (df_clean['IsGuestCustomer'] == 0).sum()
    print(f"-> Xử lý khách hàng:")
    print(f"   + Giao dịch định danh có tài khoản: {identified_count:,} dòng ({identified_count/len(df_clean)*100:.2f}%)")
    print(f"   + Giao dịch khách vãng lai (Guest Checkout gán mã -1): {guest_count:,} dòng ({guest_count/len(df_clean)*100:.2f}%)")
    print("   -> QUY TẮC BẮT BUỘC:")
    print("      1. Tính vào Fact_Sales và báo cáo Doanh thu DWH.")
    print("      2. LOẠI BỎ KHỎI RFM: Không xem mã -1 là một khách hàng thực lẻ.")

    # 4.4 Định nghĩa cách tính doanh thu nhất quán toàn hệ thống
    # LineRevenue = Quantity * UnitPrice (áp dụng chuẩn ở DWH, OLAP và Mining)
    df_clean['Quantity'] = df_clean['Quantity_Clean'].astype(int)
    df_clean['UnitPrice'] = df_clean['UnitPrice_Clean'].round(2)
    df_clean['LineRevenue'] = (df_clean['Quantity'] * df_clean['UnitPrice']).round(2)
    df_clean['TotalAmount'] = df_clean['LineRevenue']  # Alias tương thích

    # 4.5 Trích xuất chiều thời gian
    df_clean['Year'] = df_clean['InvoiceDate'].dt.year
    df_clean['Month'] = df_clean['InvoiceDate'].dt.month
    df_clean['YearMonth'] = df_clean['InvoiceDate'].dt.strftime('%Y-%m')
    df_clean['Day'] = df_clean['InvoiceDate'].dt.day
    df_clean['DayOfWeek'] = df_clean['InvoiceDate'].dt.day_name()
    df_clean['Hour'] = df_clean['InvoiceDate'].dt.hour

    # --------------------------------------------------------------------------
    # 5. ĐÁNH GIÁ MỨC ĐỘ PHÙ HỢP THEO TỪNG MỤC TIÊU PHÂN TÍCH
    # --------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print("[BƯỚC 5/6] ĐÁNH GIÁ MỨC ĐỘ PHÙ HỢP CHO DWH, RFM VÀ MARKET BASKET ANALYSIS")
    print("=" * 85)

    # Mục tiêu 1: Kho dữ liệu DWH
    print("1. Mục tiêu Kho Dữ Liệu (Fact_Sales & OLAP):")
    print(f"   + Phạm vi doanh thu kho: Chỉ bao gồm các giao dịch mua hàng thương mại hợp lệ.")
    print(f"   + Tổng số dòng nạp Fact_Sales: {len(df_clean):,} dòng")
    print(f"   + Tổng doanh thu chuẩn (LineRevenue Sum): {df_clean['LineRevenue'].sum():,.2f} GBP")

    # Mục tiêu 2: Khai phá RFM
    df_identified = df_clean[df_clean['IsGuestCustomer'] == 0]
    unique_cust = df_identified['CustomerID_Clean'].nunique()
    cust_orders = df_identified.groupby('CustomerID_Clean')['InvoiceNo'].nunique()
    cust_spend = df_identified.groupby('CustomerID_Clean')['LineRevenue'].sum()

    print("\n2. Mục tiêu Phân khúc Khách hàng RFM & K-Means:")
    print(f"   + Dữ liệu đầu vào: Chỉ lấy khách hàng định danh (CustomerID != -1).")
    print(f"   + Số lượng khách hàng định danh duy nhất: {unique_cust:,} khách")
    print(f"   + Số đơn hàng trung bình mỗi khách: {cust_orders.mean():.2f} đơn (Trung vị: {cust_orders.median():.0f}, Max: {cust_orders.max():,} đơn)")
    print(f"   + Chi tiêu trung bình mỗi khách: {cust_spend.mean():,.2f} GBP (Trung vị: {cust_spend.median():,.2f} GBP, Max: {cust_spend.max():,.2f} GBP)")

    # Mục tiêu 3: Khai phá Giỏ hàng (Market Basket Analysis - Apriori)
    invoice_items = df_clean.groupby('InvoiceNo')['StockCode'].nunique()
    total_valid_invoices = len(invoice_items)
    invoices_multi_items = (invoice_items >= 2).sum()

    print("\n3. Mục tiêu Phân tích Giỏ hàng (Market Basket Analysis - Apriori):")
    print(f"   + Dữ liệu đầu vào: Các giao dịch mua hàng hợp lệ (loại đơn hủy và cước phí).")
    print(f"   + Tổng số hóa đơn bán lẻ: {total_valid_invoices:,} hóa đơn")
    print(f"   + Số hóa đơn chứa từ 2 mặt hàng trở lên: {invoices_multi_items:,} hóa đơn ({invoices_multi_items/total_valid_invoices*100:.2f}%)")
    print(f"   + Kích thước giỏ hàng trung bình: {invoice_items.mean():.1f} mặt hàng/đơn (Trung vị: {invoice_items.median():.0f})")

    # --------------------------------------------------------------------------
    # 6. ĐỐI SOÁT SAU LÀM SẠCH & LƯU TẬP DỮ LIỆU SẠCH
    # --------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print("[BƯỚC 6/6] ĐỐI SOÁT TRƯỚC/SAU LÀM SẠCH & LƯU DỮ LIỆU SẠCH")
    print("=" * 85)

    print(f"{'Chỉ số đối soát':<35} | {'Trước làm sạch (Raw)':<22} | {'Sau làm sạch (Clean)':<22}")
    print("-" * 85)
    print(f"{'Tổng số dòng (Rows)':<35} | {total_raw_rows:>22,} | {len(df_clean):>22,}")
    print(f"{'Tổng số hóa đơn (Invoices)':<35} | {df['InvoiceNo'].nunique():>22,} | {df_clean['InvoiceNo'].nunique():>22,}")
    print(f"{'Tổng số mặt hàng (StockCode SKU)':<35} | {df['StockCode'].nunique():>22,} | {df_clean['StockCode'].nunique():>22,}")
    print(f"{'Số khách hàng định danh (Cust ID)':<35} | {df['CustomerID'].dropna().nunique():>22,} | {unique_cust:>22,}")
    print(f"{'Tổng doanh thu (Revenue GBP)':<35} | {df_work['GrossAmount'].sum():>22,.2f} | {df_clean['LineRevenue'].sum():>22,.2f}")
    print("-" * 85)

    # Lưu tệp sạch
    print(f"\nĐang ghi tệp dữ liệu sạch vào '{output_clean}'...")
    df_clean.to_csv(output_clean, index=False)
    print(f"✅ ĐÃ LƯU THÀNH CÔNG {len(df_clean):,} DÒNG SẠCH VÀO '{output_clean}'!")
    print("=" * 85)

    return df_clean, df_rejected, df_audit

if __name__ == '__main__':
    run_eda_and_cleaning()
