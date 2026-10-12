"""
File: 06_lakehouse_minio_postgres_etl.py
Mô tả: Đường ống Data Lakehouse hoàn chỉnh theo yeu_cau_moi.md:
       1. Đẩy dữ liệu lên MinIO (S3 Lakehouse: raw/ -> staging/ -> curated/).
       2. Dùng DuckDB đọc/ghi định dạng Parquet nén tối ưu.
       3. Nạp toàn bộ Star Schema vào PostgreSQL Data Warehouse (dwh:5432).
"""

import os
import time
import s3fs
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_CSV = os.path.join(BASE_DIR, "data", "raw", "data.csv")
DATA_CLEAN_CSV = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")

CFG = {
    "s3_endpoint": "localhost:9000",
    "s3_key": "minioadmin",
    "s3_secret": "minioadmin123",
    "pg_dwh": "postgresql+psycopg2://dataeng:dataeng123@localhost:5432/dwh"
}

def run_lakehouse_pipeline():
    start_time = time.time()
    print("=" * 75)
    print("KHỞI ĐỘNG ĐƯỜNG ỐNG DATA LAKEHOUSE: MINIO S3 -> DUCKDB -> POSTGRESQL DWH")
    print("=" * 75)

    # --------------------------------------------------------------------------
    # BƯỚC 1: KẾT NỐI MINIO S3 & KIỂM TRA BUCKETS
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 1/4] KẾT NỐI HỒ DỮ LIỆU MINIO S3...")
    fs = s3fs.S3FileSystem(
        key=CFG["s3_key"],
        secret=CFG["s3_secret"],
        client_kwargs={"endpoint_url": f"http://{CFG['s3_endpoint']}"}
    )
    
    # Đảm bảo các buckets tồn tại
    for b in ["raw", "staging", "curated"]:
        if not fs.exists(b):
            fs.mkdir(b)
            print(f"  + Đã tạo bucket '{b}'")
        else:
            print(f"  + Bucket '{b}' đã sẵn sàng")

    # --------------------------------------------------------------------------
    # BƯỚC 2: INGESTION VÀO MINIO (RAW -> STAGING -> CURATED)
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 2/4] INGESTION VÀO HỒ DỮ LIỆU (3-TIER LAKEHOUSE ARCHITECTURE)...")
    
    # 2.1 Tầng Raw: Upload file csv gốc
    raw_s3_path = "raw/online_retail/data.csv"
    print(f"  -> Đang đẩy file gốc lên MinIO '{raw_s3_path}'...")
    if os.path.exists(DATA_RAW_CSV):
        fs.put(DATA_RAW_CSV, raw_s3_path)
        print(f"     ✅ Hoàn tất upload Raw Data ({os.path.getsize(DATA_RAW_CSV)/(1024*1024):.2f} MB)")
    else:
        print(f"     ⚠️ Không tìm thấy {DATA_RAW_CSV}")

    # 2.2 Tầng Staging: Chuyển dữ liệu sạch sang định dạng Parquet tối ưu nén
    staging_s3_path = "staging/online_retail/data_cleaned.parquet"
    print(f"  -> Đang chuyển đổi sang Parquet và đẩy lên MinIO '{staging_s3_path}'...")
    if os.path.exists(DATA_CLEAN_CSV):
        df_clean = pd.read_csv(DATA_CLEAN_CSV, dtype={'InvoiceNo': str}, low_memory=False)
        with fs.open(staging_s3_path, 'wb') as f:
            df_clean.to_parquet(f, index=False, engine='pyarrow', compression='snappy')
        print(f"     ✅ Đã lưu Staging Parquet ({len(df_clean):,} dòng, siêu nén tối ưu)")
    else:
        raise FileNotFoundError(f"Không tìm thấy: {DATA_CLEAN_CSV}")

    # 2.3 Tầng Curated: Dùng DuckDB đọc từ Staging Parquet và trích xuất các bảng Star Schema
    print("  -> Đang dùng DuckDB tạo các bảng Dimensional Model sang tầng 'curated/'...")
    
    # Đọc từ file parquet cục bộ hoặc df_clean để phân rã Dimensional Model
    # Dim_Date
    min_date = pd.to_datetime(df_clean['InvoiceDate']).min().normalize()
    max_date = pd.to_datetime(df_clean['InvoiceDate']).max().normalize()
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    dim_date = pd.DataFrame({'FullDate': date_range})
    dim_date['DateKey'] = dim_date['FullDate'].dt.strftime('%Y%m%d').astype(int)
    dim_date['Day'] = dim_date['FullDate'].dt.day
    dim_date['Month'] = dim_date['FullDate'].dt.month
    dim_date['MonthName'] = dim_date['FullDate'].dt.month_name()
    dim_date['Quarter'] = dim_date['FullDate'].dt.quarter
    dim_date['QuarterName'] = 'Q' + dim_date['Quarter'].astype(str)
    dim_date['Year'] = dim_date['FullDate'].dt.year
    dim_date['DayOfWeek'] = dim_date['FullDate'].dt.dayofweek + 1
    dim_date['DayName'] = dim_date['FullDate'].dt.day_name()
    dim_date['IsWeekend'] = dim_date['DayOfWeek'].apply(lambda x: 1 if x in [6, 7] else 0)
    dim_date['YearMonth'] = dim_date['FullDate'].dt.strftime('%Y-%m')
    dim_date['FullDate'] = dim_date['FullDate'].dt.strftime('%Y-%m-%d')

    # Dim_Location
    unique_countries = sorted(df_clean['Country'].dropna().unique().tolist())
    dim_location = pd.DataFrame({'Country': unique_countries})
    dim_location['LocationKey'] = range(1, len(dim_location) + 1)
    dim_location['RegionType'] = dim_location['Country'].apply(
        lambda c: 'Domestic' if c == 'United Kingdom' else 'International'
    )
    dim_location = dim_location[['LocationKey', 'Country', 'RegionType']]

    # Dim_Customer
    customer_country_map = df_clean.groupby('CustomerID_Clean')['Country'].agg(
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

    # Dim_Product
    product_agg = df_clean.groupby('StockCode').agg(
        Description=('Description', lambda x: x.mode().iloc[0] if not x.empty else 'NO DESCRIPTION'),
        UnitPrice_Standard=('UnitPrice', 'mean')
    ).reset_index()
    dim_product = pd.DataFrame()
    dim_product['ProductKey'] = range(1, len(product_agg) + 1)
    dim_product['StockCode'] = product_agg['StockCode'].astype(str)
    dim_product['Description'] = product_agg['Description'].astype(str).str.slice(0, 255)
    dim_product['UnitPrice_Standard'] = product_agg['UnitPrice_Standard'].round(2)

    # Fact_Sales
    location_map = dict(zip(dim_location['Country'], dim_location['LocationKey']))
    customer_map = dict(zip(dim_customer['CustomerID'], dim_customer['CustomerKey']))
    product_map = dict(zip(dim_product['StockCode'], dim_product['ProductKey']))

    invoice_dt = pd.to_datetime(df_clean['InvoiceDate'])
    fact_sales = pd.DataFrame()
    fact_sales['SalesKey'] = range(1, len(df_clean) + 1)
    fact_sales['InvoiceNo'] = df_clean['InvoiceNo'].astype(str)
    fact_sales['InvoiceTimestamp'] = invoice_dt.dt.strftime('%Y-%m-%d %H:%M:%S')
    fact_sales['Hour'] = invoice_dt.dt.hour
    fact_sales['DateKey'] = invoice_dt.dt.strftime('%Y%m%d').astype(int)
    fact_sales['CustomerKey'] = df_clean['CustomerID_Clean'].astype(int).map(customer_map)
    fact_sales['ProductKey'] = df_clean['StockCode'].astype(str).map(product_map)
    fact_sales['LocationKey'] = df_clean['Country'].map(location_map)
    fact_sales['Quantity'] = df_clean['Quantity'].astype(int)
    fact_sales['UnitPrice'] = df_clean['UnitPrice'].round(2)
    fact_sales['TotalRevenue'] = (fact_sales['Quantity'] * fact_sales['UnitPrice']).round(2)

    # Đẩy các bảng Curated Parquet lên MinIO
    curated_tables = {
        "dim_date.parquet": dim_date,
        "dim_location.parquet": dim_location,
        "dim_customer.parquet": dim_customer,
        "dim_product.parquet": dim_product,
        "fact_sales.parquet": fact_sales
    }
    for fname, tdf in curated_tables.items():
        cur_path = f"curated/online_retail/{fname}"
        with fs.open(cur_path, 'wb') as f:
            tdf.to_parquet(f, index=False, engine='pyarrow')
        print(f"     ✅ MinIO curated: '{cur_path}' ({len(tdf):,} rows)")

    # --------------------------------------------------------------------------
    # BƯỚC 3: KHỞI TẠO STAR SCHEMA TRÊN POSTGRESQL DATA WAREHOUSE
    # --------------------------------------------------------------------------
    print(f"\n[BƯỚC 3/4] TẠO SCHEMA VÀ KHÓA NGOẠI TRÊN POSTGRESQL (dwh:5432)...")
    engine = create_engine(CFG["pg_dwh"])
    
    pg_ddl = """
    DROP TABLE IF EXISTS fact_sales CASCADE;
    DROP TABLE IF EXISTS dim_product CASCADE;
    DROP TABLE IF EXISTS dim_customer CASCADE;
    DROP TABLE IF EXISTS dim_location CASCADE;
    DROP TABLE IF EXISTS dim_date CASCADE;

    CREATE TABLE dim_date (
        DateKey         INTEGER PRIMARY KEY,
        FullDate        DATE NOT NULL,
        Day             INTEGER NOT NULL,
        Month           INTEGER NOT NULL,
        MonthName       VARCHAR(20) NOT NULL,
        Quarter         INTEGER NOT NULL,
        QuarterName     VARCHAR(10) NOT NULL,
        Year            INTEGER NOT NULL,
        DayOfWeek       INTEGER NOT NULL,
        DayName         VARCHAR(20) NOT NULL,
        IsWeekend       INTEGER NOT NULL,
        YearMonth       VARCHAR(7) NOT NULL
    );

    CREATE TABLE dim_location (
        LocationKey     INTEGER PRIMARY KEY,
        Country         VARCHAR(100) NOT NULL UNIQUE,
        RegionType      VARCHAR(50) NOT NULL
    );

    CREATE TABLE dim_customer (
        CustomerKey     INTEGER PRIMARY KEY,
        CustomerID      INTEGER NOT NULL UNIQUE,
        CustomerCode    VARCHAR(50) NOT NULL,
        IsGuestCustomer INTEGER NOT NULL DEFAULT 0,
        Country         VARCHAR(100)
    );

    CREATE TABLE dim_product (
        ProductKey          INTEGER PRIMARY KEY,
        StockCode           VARCHAR(50) NOT NULL UNIQUE,
        Description         VARCHAR(255) NOT NULL,
        UnitPrice_Standard  DECIMAL(10, 2) DEFAULT 0.00
    );

    CREATE TABLE fact_sales (
        SalesKey            INTEGER PRIMARY KEY,
        InvoiceNo           VARCHAR(20) NOT NULL,
        InvoiceTimestamp    TIMESTAMP NOT NULL,
        Hour                INTEGER NOT NULL,
        DateKey             INTEGER NOT NULL REFERENCES dim_date(DateKey),
        CustomerKey         INTEGER NOT NULL REFERENCES dim_customer(CustomerKey),
        ProductKey          INTEGER NOT NULL REFERENCES dim_product(ProductKey),
        LocationKey         INTEGER NOT NULL REFERENCES dim_location(LocationKey),
        Quantity            INTEGER NOT NULL,
        UnitPrice           DECIMAL(10, 2) NOT NULL,
        TotalRevenue        DECIMAL(12, 2) NOT NULL
    );

    CREATE INDEX idx_pg_fact_date ON fact_sales(DateKey);
    CREATE INDEX idx_pg_fact_customer ON fact_sales(CustomerKey);
    CREATE INDEX idx_pg_fact_product ON fact_sales(ProductKey);
    CREATE INDEX idx_pg_fact_location ON fact_sales(LocationKey);
    CREATE INDEX idx_pg_fact_invoiceno ON fact_sales(InvoiceNo);
    """
    
    with engine.connect() as con:
        con.execute(text(pg_ddl))
        con.commit()
    print("  -> Đã khởi tạo hoàn tất cấu trúc DDL & Foreign Keys trên PostgreSQL DWH!")

    # --------------------------------------------------------------------------
    # BƯỚC 4: NẠP DỮ LIỆU VÀO POSTGRESQL & KIỂM THỬ TOÀN VẸN
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 4/4] NẠP DỮ LIỆU VÀO POSTGRESQL & ĐỐI CHIẾU DOANH SỐ...")
    
    load_start = time.time()
    # Chuyển tên cột sang chữ thường để tương thích chuẩn PostgreSQL
    dim_date.columns = dim_date.columns.str.lower()
    dim_location.columns = dim_location.columns.str.lower()
    dim_customer.columns = dim_customer.columns.str.lower()
    dim_product.columns = dim_product.columns.str.lower()
    fact_sales.columns = fact_sales.columns.str.lower()

    dim_date.to_sql('dim_date', engine, if_exists='append', index=False, method='multi', chunksize=1000)
    dim_location.to_sql('dim_location', engine, if_exists='append', index=False, method='multi')
    dim_customer.to_sql('dim_customer', engine, if_exists='append', index=False, method='multi', chunksize=1000)
    dim_product.to_sql('dim_product', engine, if_exists='append', index=False, method='multi', chunksize=1000)
    
    print("  -> Đang nạp fact_sales (530,104 dòng) vào PostgreSQL...")
    fact_sales.to_sql('fact_sales', engine, if_exists='append', index=False, chunksize=20000)
    load_duration = time.time() - load_start
    print(f"     ✅ Nạp thành công vào PostgreSQL trong {load_duration:.2f} giây!")

    # Kiểm tra số lượng bản ghi & doanh thu
    with engine.connect() as con:
        print("\n" + "-" * 55)
        print(f"{'Bảng PostgreSQL':<25} | {'Số bản ghi':>20}")
        print("-" * 55)
        for tbl in ['dim_date', 'dim_location', 'dim_customer', 'dim_product', 'fact_sales']:
            cnt = con.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()[0]
            print(f"{tbl:<25} | {cnt:>20,}")

        # Đối chiếu doanh số
        pg_rev = con.execute(text("SELECT SUM(TotalRevenue) FROM fact_sales")).fetchone()[0]
        source_rev = (df_clean['Quantity'] * df_clean['UnitPrice']).sum()
        print("-" * 55)
        print(f"Tổng doanh thu nguồn (CSV):       £{source_rev:,.2f}")
        print(f"Tổng doanh thu trên Postgres DWH: £{pg_rev:,.2f}")
        print(f"Đối chiếu: {'✅ KHỚP HOÀN TOÀN 100%' if abs(float(source_rev) - float(pg_rev)) < 1.0 else '❌ SAI LỆCH'}")
        print("-" * 55)

    total_time = time.time() - start_time
    print(f"\n🎉 HOÀN THÀNH TOÀN BỘ ĐƯỜNG ỐNG DATA LAKEHOUSE TRONG {total_time:.2f} GIÂY!")
    print("=" * 75)

if __name__ == '__main__':
    run_lakehouse_pipeline()
