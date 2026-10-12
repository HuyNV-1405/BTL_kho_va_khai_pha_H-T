"""
File: 01_eda_and_cleaning.py
Mô tả: Khám phá dữ liệu (EDA), phân tích dị biệt và tiền xử lý làm sạch dữ liệu Online Retail.
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_eda_and_cleaning(
    input_file=None, 
    output_file=None
):
    if input_file is None:
        input_file = os.path.join(BASE_DIR, "data", "raw", "data.csv")
    if output_file is None:
        output_file = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
        
    print(f"Đang đọc dữ liệu từ '{input_file}'...")
    # Thử đọc với encoding utf-8 hoặc ISO-8859-1 (thường gặp ở dataset Online Retail)
    try:
        df = pd.read_csv(input_file, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, encoding='ISO-8859-1')
        
    print(f"- Tổng số dòng ban đầu: {len(df):,}")
    print(f"- Tổng số cột: {len(df.columns)}")
    print(f"- Các cột: {list(df.columns)}")
    
    print("\n" + "=" * 60)
    print("BƯỚC 2: KIỂM TRA CHẤT LƯỢNG DỮ LIỆU (DATA QUALITY CHECK)")
    print("=" * 60)
    
    # 2.1 Kiểm tra giá trị khuyết thiếu
    null_counts = df.isnull().sum()
    null_pct = (null_counts / len(df)) * 100
    missing_report = pd.DataFrame({"Missing Count": null_counts, "Percentage (%)": null_pct.round(2)})
    print("\nThống kê giá trị khuyết thiếu (Missing Values):")
    print(missing_report[missing_report["Missing Count"] > 0])
    
    # 2.2 Kiểm tra đơn hàng hủy (Cancelled orders: InvoiceNo bắt đầu bằng 'C')
    cancelled_mask = df['InvoiceNo'].astype(str).str.startswith('C')
    cancelled_count = cancelled_mask.sum()
    print(f"\n- Số hóa đơn hủy (bắt đầu bằng 'C'): {cancelled_count:,} ({cancelled_count/len(df)*100:.2f}%)")
    
    # 2.3 Kiểm tra số lượng và đơn giá âm / bằng 0
    neg_quantity = (df['Quantity'] <= 0).sum()
    neg_price = (df['UnitPrice'] <= 0).sum()
    print(f"- Số dòng có Quantity <= 0: {neg_quantity:,}")
    print(f"- Số dòng có UnitPrice <= 0: {neg_price:,}")
    
    print("\n" + "=" * 60)
    print("BƯỚC 3: TIỀN XỬ LÝ & LÀM SẠCH (DATA CLEANING)")
    print("=" * 60)
    
    df_clean = df.copy()
    
    # 3.1 Chuẩn hóa định dạng ngày tháng
    print("-> Đang chuẩn hóa cột 'InvoiceDate' sang datetime...")
    df_clean['InvoiceDate'] = pd.to_datetime(df_clean['InvoiceDate'])
    
    # 3.2 Chuẩn hóa mô tả sản phẩm (chữ hoa, bỏ khoảng trắng)
    print("-> Đang chuẩn hóa cột 'Description'...")
    df_clean['Description'] = df_clean['Description'].astype(str).str.strip().str.upper()
    
    # 3.3 Loại bỏ các đơn hàng hủy và số lượng/đơn giá bất hợp lệ
    # Trong bài toán phân tích doanh thu & giỏ hàng, ta tập trung vào các giao dịch mua hàng hợp lệ
    print("-> Đang lọc bỏ đơn hàng hủy và số lượng / đơn giá không hợp lệ...")
    valid_mask = (~cancelled_mask) & (df_clean['Quantity'] > 0) & (df_clean['UnitPrice'] > 0)
    df_clean = df_clean[valid_mask].copy()
    
    # 3.4 Xử lý CustomerID khuyết thiếu
    # Để phân tích giỏ hàng/doanh thu vẫn giữ được bản ghi, ta gán mã khách vãng lai (Guest: -1)
    df_clean['IsGuestCustomer'] = df_clean['CustomerID'].isnull().astype(int)
    df_clean['CustomerID_Clean'] = df_clean['CustomerID'].fillna(-1).astype(int)
    
    # 3.5 Tính toán chỉ số phái sinh
    df_clean['TotalAmount'] = df_clean['Quantity'] * df_clean['UnitPrice']
    
    # 3.6 Trích xuất các thuộc tính thời gian phục vụ Data Warehouse
    df_clean['Year'] = df_clean['InvoiceDate'].dt.year
    df_clean['Month'] = df_clean['InvoiceDate'].dt.month
    df_clean['YearMonth'] = df_clean['InvoiceDate'].dt.to_period('M').astype(str)
    df_clean['Day'] = df_clean['InvoiceDate'].dt.day
    df_clean['DayOfWeek'] = df_clean['InvoiceDate'].dt.day_name()
    df_clean['Hour'] = df_clean['InvoiceDate'].dt.hour
    
    print(f"\n=> Tổng số dòng sau khi làm sạch: {len(df_clean):,} (Giữ lại {len(df_clean)/len(df)*100:.2f}%)")
    
    print("\n" + "=" * 60)
    print("BƯỚC 4: THỐNG KÊ TỔNG QUAN SAU KHI LÀM SẠCH")
    print("=" * 60)
    print(f"- Khoảng thời gian: từ {df_clean['InvoiceDate'].min()} đến {df_clean['InvoiceDate'].max()}")
    print(f"- Tổng doanh thu: {df_clean['TotalAmount'].sum():,.2f} GBP")
    print(f"- Tổng số đơn hàng: {df_clean['InvoiceNo'].nunique():,}")
    print(f"- Tổng số mặt hàng khác nhau: {df_clean['StockCode'].nunique():,}")
    print(f"- Tổng số khách hàng định danh: {df_clean[df_clean['CustomerID_Clean'] != -1]['CustomerID_Clean'].nunique():,}")
    print(f"- Số quốc gia tham gia giao dịch: {df_clean['Country'].nunique():,}")
    
    # Top 5 quốc gia có doanh thu cao nhất
    top_countries = df_clean.groupby('Country')['TotalAmount'].sum().sort_values(ascending=False).head(5)
    print("\nTop 5 quốc gia có doanh thu cao nhất:")
    for country, rev in top_countries.items():
        print(f"  + {country}: {rev:,.2f} GBP ({rev / df_clean['TotalAmount'].sum() * 100:.2f}%)")
        
    print("\n" + "=" * 60)
    print("BƯỚC 5: LƯU TẬP DỮ LIỆU SẠCH")
    print("=" * 60)
    print(f"Đang lưu file '{output_file}'...")
    df_clean.to_csv(output_file, index=False)
    print(f"Đã lưu thành công file '{output_file}'!")
    print("=" * 60)
    return df_clean

if __name__ == '__main__':
    run_eda_and_cleaning()
