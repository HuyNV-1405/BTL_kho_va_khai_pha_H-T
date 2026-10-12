"""
File: 03_etl_pipeline.py
Mô tả: Đường ống ETL (Extract - Transform - Load) chuẩn hóa từ data_cleaned.csv
       vào Kho Dữ Liệu SQLite (retail_dwh.db) theo mô hình Star Schema.
"""

import os
import sys
import time
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_etl_pipeline(
    csv_file=None,
    db_file=None,
    ddl_file=None
):
    if csv_file is None:
        csv_file = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
    if db_file is None:
        db_file = os.path.join(BASE_DIR, "database", "retail_dwh.db")
    if ddl_file is None:
        ddl_file = os.path.join(BASE_DIR, "database", "02_schema_ddl.sql")
    start_total_time = time.time()
    print("=" * 70)
    print("BẮT ĐẦU ĐƯỜNG ỐNG ETL - ONLINE RETAIL DATA WAREHOUSE")
    print("=" * 70)

    # --------------------------------------------------------------------------
    # BƯỚC 1: TRÍCH XUẤT (EXTRACT)
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 1/4] EXTRACT: Đọc dữ liệu từ file làm sạch...")
    if not os.path.exists(csv_file):
        eda_script = os.path.join(BASE_DIR, "scripts", "01_eda_and_cleaning.py")
        if os.path.exists(eda_script):
            print(f"- Không tìm thấy '{csv_file}'. Tự động chạy '{eda_script}'...")
            from importlib.machinery import SourceFileLoader
            eda_module = SourceFileLoader("eda", eda_script).load_module()
            eda_module.run_eda_and_cleaning()
        else:
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {csv_file}")

    df = pd.read_csv(csv_file, dtype={'InvoiceNo': str}, low_memory=False)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    total_raw_rows = len(df)
    print(f"-> Đã trích xuất thành công {total_raw_rows:,} bản ghi giao dịch.")

    # --------------------------------------------------------------------------
    # BƯỚC 2: BIẾN ĐỔI (TRANSFORM) - TẠO CÁC BẢNG DIMENSION VÀ FACT
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 2/4] TRANSFORM: Chuẩn bị các Dimension Tables và Fact Table...")
    
    # 2.1 Transform: Dim_Date (Bao phủ toàn bộ dải ngày từ min đến max)
    print("  -> Đang xây dựng Dim_Date...")
    min_date = df['InvoiceDate'].min().normalize()
    max_date = df['InvoiceDate'].max().normalize()
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    
    dim_date = pd.DataFrame({'FullDate': date_range})
    dim_date['DateKey'] = dim_date['FullDate'].dt.strftime('%Y%m%d').astype(int)
    dim_date['Day'] = dim_date['FullDate'].dt.day
    dim_date['Month'] = dim_date['FullDate'].dt.month
    dim_date['MonthName'] = dim_date['FullDate'].dt.month_name()
    dim_date['Quarter'] = dim_date['FullDate'].dt.quarter
    dim_date['QuarterName'] = 'Q' + dim_date['Quarter'].astype(str)
    dim_date['Year'] = dim_date['FullDate'].dt.year
    dim_date['DayOfWeek'] = dim_date['FullDate'].dt.dayofweek + 1  # 1 = Monday, 7 = Sunday
    dim_date['DayName'] = dim_date['FullDate'].dt.day_name()
    dim_date['IsWeekend'] = dim_date['DayOfWeek'].apply(lambda x: 1 if x in [6, 7] else 0)
    dim_date['YearMonth'] = dim_date['FullDate'].dt.strftime('%Y-%m')
    dim_date['FullDate'] = dim_date['FullDate'].dt.strftime('%Y-%m-%d')
    print(f"     + Dim_Date: {len(dim_date):,} ngày (Từ {min_date.strftime('%Y-%m-%d')} đến {max_date.strftime('%Y-%m-%d')})")

    # 2.2 Transform: Dim_Location
    print("  -> Đang xây dựng Dim_Location...")
    unique_countries = sorted(df['Country'].dropna().unique().tolist())
    dim_location = pd.DataFrame({'Country': unique_countries})
    dim_location['LocationKey'] = range(1, len(dim_location) + 1)
    dim_location['RegionType'] = dim_location['Country'].apply(
        lambda c: 'Domestic' if c == 'United Kingdom' else 'International'
    )
    dim_location = dim_location[['LocationKey', 'Country', 'RegionType']]
    print(f"     + Dim_Location: {len(dim_location):,} quốc gia/vùng lãnh thổ")

    # 2.3 Transform: Dim_Customer
    print("  -> Đang xây dựng Dim_Customer...")
    customer_country_map = df.groupby('CustomerID_Clean')['Country'].agg(
        lambda x: x.mode().iloc[0] if not x.empty else 'Unknown'
    ).reset_index()
    
    dim_customer = pd.DataFrame()
    dim_customer['CustomerID'] = customer_country_map['CustomerID_Clean'].astype(int)
    dim_customer['Country'] = customer_country_map['Country']
    dim_customer['CustomerKey'] = range(1, len(dim_customer) + 1)
    dim_customer['IsGuestCustomer'] = dim_customer['CustomerID'].apply(lambda cid: 1 if cid == -1 else 0)
    dim_customer['CustomerCode'] = dim_customer['CustomerID'].apply(
        lambda cid: 'GUEST' if cid == -1 else f"CUST-{cid}"
    )
    dim_customer = dim_customer[['CustomerKey', 'CustomerID', 'CustomerCode', 'IsGuestCustomer', 'Country']]
    print(f"     + Dim_Customer: {len(dim_customer):,} khách hàng (bao gồm khách vãng lai GUEST)")

    # 2.4 Transform: Dim_Product
    print("  -> Đang xây dựng Dim_Product...")
    product_agg = df.groupby('StockCode').agg(
        Description=('Description', lambda x: x.mode().iloc[0] if not x.empty else 'NO DESCRIPTION'),
        UnitPrice_Standard=('UnitPrice', 'mean')
    ).reset_index()
    
    dim_product = pd.DataFrame()
    dim_product['ProductKey'] = range(1, len(product_agg) + 1)
    dim_product['StockCode'] = product_agg['StockCode'].astype(str)
    dim_product['Description'] = product_agg['Description'].astype(str).str.slice(0, 255)
    dim_product['UnitPrice_Standard'] = product_agg['UnitPrice_Standard'].round(2)
    print(f"     + Dim_Product: {len(dim_product):,} sản phẩm")

    # 2.5 Transform: Fact_Sales (Ghép nối Surrogate Keys)
    print("  -> Đang chuẩn bị Fact_Sales & ánh xạ khóa đại diện (Surrogate Keys)...")
    
    # Tạo map tra cứu nhanh (Dictionary Lookup để tối ưu tốc độ vượt trội)
    location_map = dict(zip(dim_location['Country'], dim_location['LocationKey']))
    customer_map = dict(zip(dim_customer['CustomerID'], dim_customer['CustomerKey']))
    product_map = dict(zip(dim_product['StockCode'], dim_product['ProductKey']))

    fact_sales = pd.DataFrame()
    fact_sales['InvoiceNo'] = df['InvoiceNo'].astype(str)
    fact_sales['InvoiceTimestamp'] = df['InvoiceDate'].dt.strftime('%Y-%m-%d %H:%M:%S')
    fact_sales['Hour'] = df['InvoiceDate'].dt.hour
    fact_sales['DateKey'] = df['InvoiceDate'].dt.strftime('%Y%m%d').astype(int)
    
    # Map Foreign Keys
    fact_sales['CustomerKey'] = df['CustomerID_Clean'].astype(int).map(customer_map)
    fact_sales['ProductKey'] = df['StockCode'].astype(str).map(product_map)
    fact_sales['LocationKey'] = df['Country'].map(location_map)
    
    fact_sales['Quantity'] = df['Quantity'].astype(int)
    fact_sales['UnitPrice'] = df['UnitPrice'].round(2)
    fact_sales['TotalRevenue'] = (fact_sales['Quantity'] * fact_sales['UnitPrice']).round(2)
    
    fact_sales['SalesKey'] = range(1, len(fact_sales) + 1)
    
    # Sắp xếp đúng thứ tự cột DDL
    fact_cols = [
        'SalesKey', 'InvoiceNo', 'InvoiceTimestamp', 'Hour',
        'DateKey', 'CustomerKey', 'ProductKey', 'LocationKey',
        'Quantity', 'UnitPrice', 'TotalRevenue'
    ]
    fact_sales = fact_sales[fact_cols]
    print(f"     + Fact_Sales: {len(fact_sales):,} dòng giao dịch hoàn chỉnh")

    # --------------------------------------------------------------------------
    # BƯỚC 3: NẠP DỮ LIỆU VÀO DATABASE (LOAD)
    # --------------------------------------------------------------------------
    print(f"\n[BƯỚC 3/4] LOAD: Khởi tạo database và nạp dữ liệu vào '{db_file}'...")
    
    # Xóa database cũ nếu cần đảm bảo môi trường sạch
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"  -> Đã làm sạch file database cũ: {db_file}")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Thực thi DDL khởi tạo schema
    if os.path.exists(ddl_file):
        print(f"  -> Thực thi DDL từ '{ddl_file}'...")
        with open(ddl_file, 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
        conn.commit()
    else:
        raise FileNotFoundError(f"Không tìm thấy kịch bản DDL: {ddl_file}")

    # Nạp dữ liệu các bảng theo thứ tự Dimension -> Fact
    load_start = time.time()
    
    print("  -> Đang nạp Dim_Date...")
    dim_date.to_sql('Dim_Date', conn, if_exists='append', index=False)
    
    print("  -> Đang nạp Dim_Location...")
    dim_location.to_sql('Dim_Location', conn, if_exists='append', index=False)
    
    print("  -> Đang nạp Dim_Customer...")
    dim_customer.to_sql('Dim_Customer', conn, if_exists='append', index=False)
    
    print("  -> Đang nạp Dim_Product...")
    dim_product.to_sql('Dim_Product', conn, if_exists='append', index=False)

    print("  -> Đang nạp Fact_Sales (Batch Load 50,000 dòng/batch)...")
    fact_sales.to_sql('Fact_Sales', conn, if_exists='append', index=False, chunksize=50000)
    
    conn.commit()
    load_duration = time.time() - load_start
    print(f"-> Nạp hoàn tất toàn bộ dữ liệu vào cơ sở dữ liệu trong {load_duration:.2f} giây!")

    # --------------------------------------------------------------------------
    # BƯỚC 4: KIỂM THỬ TÍNH TOÀN VẸN DỮ LIỆU (DATA INTEGRITY CHECKS)
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 4/4] KIỂM THỬ TÍNH TOÀN VẸN (DATA INTEGRITY CHECKS)")
    print("-" * 70)
    
    tables = ['Dim_Date', 'Dim_Location', 'Dim_Customer', 'Dim_Product', 'Fact_Sales']
    print(f"{'Tên Bảng (Table)':<20} | {'Số lượng bản ghi (Rows)':<25}")
    print("-" * 50)
    for table in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<20} | {count:>15,}")

    # Kiểm tra khóa ngoại mồ côi (Orphan Records)
    orphan_date = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE DateKey NOT IN (SELECT DateKey FROM Dim_Date)").fetchone()[0]
    orphan_cust = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE CustomerKey NOT IN (SELECT CustomerKey FROM Dim_Customer)").fetchone()[0]
    orphan_prod = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE ProductKey NOT IN (SELECT ProductKey FROM Dim_Product)").fetchone()[0]
    orphan_loc = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE LocationKey NOT IN (SELECT LocationKey FROM Dim_Location)").fetchone()[0]
    
    print("\nKiểm tra ràng buộc khóa ngoại (Referential Integrity):")
    print(f"  + Lỗi DateKey mồ côi:     {orphan_date} bản ghi {'[OK]' if orphan_date == 0 else '[LỖI]'}")
    print(f"  + Lỗi CustomerKey mồ côi: {orphan_cust} bản ghi {'[OK]' if orphan_cust == 0 else '[LỖI]'}")
    print(f"  + Lỗi ProductKey mồ côi:  {orphan_prod} bản ghi {'[OK]' if orphan_prod == 0 else '[LỖI]'}")
    print(f"  + Lỗi LocationKey mồ côi: {orphan_loc} bản ghi {'[OK]' if orphan_loc == 0 else '[LỖI]'}")

    # Đối chiếu tổng doanh thu giữa nguồn và DWH
    source_revenue = (df['Quantity'] * df['UnitPrice']).sum()
    dwh_revenue = cursor.execute("SELECT SUM(TotalRevenue) FROM Fact_Sales").fetchone()[0]
    rev_diff = abs(source_revenue - dwh_revenue)
    print("\nKiểm tra đối chiếu doanh thu (Reconciliation):")
    print(f"  + Doanh thu từ file sạch (Source):  {source_revenue:,.2f} GBP")
    print(f"  + Doanh thu trong Fact_Sales (DWH):  {dwh_revenue:,.2f} GBP")
    print(f"  + Sai lệch (Difference):             {rev_diff:,.4f} GBP {'[KHỚP 100%]' if rev_diff < 1.0 else '[CẢNH BÁO]'}")

    conn.close()
    
    total_duration = time.time() - start_total_time
    print("=" * 70)
    print(f"HOÀN THÀNH ETL PIPELINE TRONG {total_duration:.2f} GIÂY!")
    print(f"File kho dữ liệu đã sẵn sàng: '{os.path.abspath(db_file)}'")
    print("=" * 70)

if __name__ == '__main__':
    run_etl_pipeline()
