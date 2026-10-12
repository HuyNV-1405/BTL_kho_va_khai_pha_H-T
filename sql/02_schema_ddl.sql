-- ==============================================================================
-- ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ONLINE RETAIL DATA WAREHOUSE)
-- GIAI ĐOẠN 2: THIẾT KẾ MÔ HÌNH DỮ LIỆU ĐA CHIỀU (STAR SCHEMA DDL)
-- File: 02_schema_ddl.sql
-- Mô tả: Kịch bản DDL tạo bảng Fact và các Dimension chuẩn Star Schema.
--        Tương thích: SQLite, DuckDB, PostgreSQL, MySQL.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. BẢNG CHIỀU THỜI GIAN (Dim_Date)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS Fact_Sales;
DROP TABLE IF EXISTS Dim_Product;
DROP TABLE IF EXISTS Dim_Customer;
DROP TABLE IF EXISTS Dim_Location;
DROP TABLE IF EXISTS Dim_Date;

CREATE TABLE Dim_Date (
    DateKey         INTEGER PRIMARY KEY,            -- Định dạng YYYYMMDD (vd: 20101201)
    FullDate        DATE NOT NULL,                  -- Ngày đầy đủ (YYYY-MM-DD)
    Day             INTEGER NOT NULL,               -- Ngày trong tháng (1 - 31)
    Month           INTEGER NOT NULL,               -- Tháng (1 - 12)
    MonthName       VARCHAR(20) NOT NULL,           -- Tên tháng tiếng Anh (January, February, ...)
    Quarter         INTEGER NOT NULL,               -- Quý (1 - 4)
    QuarterName     VARCHAR(10) NOT NULL,           -- Tên quý (Q1, Q2, Q3, Q4)
    Year            INTEGER NOT NULL,               -- Năm (2010, 2011)
    DayOfWeek       INTEGER NOT NULL,               -- Thứ trong tuần (1 = Monday, ..., 7 = Sunday)
    DayName         VARCHAR(20) NOT NULL,           -- Tên thứ (Monday, Tuesday, ...)
    IsWeekend       INTEGER NOT NULL,               -- 1 nếu là cuối tuần (Sat/Sun), 0 nếu là ngày thường
    YearMonth       VARCHAR(7) NOT NULL             -- Định dạng YYYY-MM
);

-- ------------------------------------------------------------------------------
-- 2. BẢNG CHIỀU VỊ TRÍ ĐỊA LÝ (Dim_Location)
-- ------------------------------------------------------------------------------
CREATE TABLE Dim_Location (
    LocationKey     INTEGER PRIMARY KEY,            -- Surrogate Key tự tăng
    Country         VARCHAR(100) NOT NULL UNIQUE,   -- Tên quốc gia
    RegionType      VARCHAR(50) NOT NULL            -- Phân loại vùng: 'Domestic' (United Kingdom) / 'International'
);

-- ------------------------------------------------------------------------------
-- 3. BẢNG CHIỀU KHÁCH HÀNG (Dim_Customer)
-- ------------------------------------------------------------------------------
CREATE TABLE Dim_Customer (
    CustomerKey     INTEGER PRIMARY KEY,            -- Surrogate Key tự tăng
    CustomerID      INTEGER NOT NULL UNIQUE,        -- Natural Key từ hệ thống nghiệp vụ (-1: Khách vãng lai)
    CustomerCode    VARCHAR(50) NOT NULL,           -- Mã hiển thị (vd: 'CUST-17850', 'GUEST')
    IsGuestCustomer INTEGER NOT NULL DEFAULT 0,     -- 1: Khách vãng lai, 0: Khách hàng thành viên
    Country         VARCHAR(100)                    -- Quốc gia đăng ký của khách hàng
);

-- ------------------------------------------------------------------------------
-- 4. BẢNG CHIỀU SẢN PHẨM (Dim_Product)
-- ------------------------------------------------------------------------------
CREATE TABLE Dim_Product (
    ProductKey          INTEGER PRIMARY KEY,        -- Surrogate Key tự tăng
    StockCode           VARCHAR(50) NOT NULL UNIQUE,-- Natural Key mã sản phẩm
    Description         VARCHAR(255) NOT NULL,      -- Tên/Mô tả sản phẩm chuẩn hóa
    UnitPrice_Standard  DECIMAL(10, 2) DEFAULT 0.00 -- Đơn giá tham chiếu trung bình
);

-- ------------------------------------------------------------------------------
-- 5. BẢNG SỰ KIỆN DOANH SỐ (Fact_Sales)
-- Độ hạt (Granularity): Từng dòng mặt hàng trong mỗi hóa đơn (Line-item level)
-- ------------------------------------------------------------------------------
CREATE TABLE Fact_Sales (
    SalesKey            INTEGER PRIMARY KEY,        -- Surrogate Key dòng giao dịch
    InvoiceNo           VARCHAR(20) NOT NULL,       -- Mã hóa đơn bán hàng (Degenerate Dimension)
    InvoiceTimestamp    TIMESTAMP NOT NULL,         -- Thời gian giao dịch chi tiết (YYYY-MM-DD HH:MM:SS)
    Hour                INTEGER NOT NULL,           -- Khung giờ giao dịch (0 - 23)
    DateKey             INTEGER NOT NULL,           -- Khóa ngoại đến Dim_Date
    CustomerKey         INTEGER NOT NULL,           -- Khóa ngoại đến Dim_Customer
    ProductKey          INTEGER NOT NULL,           -- Khóa ngoại đến Dim_Product
    LocationKey         INTEGER NOT NULL,           -- Khóa ngoại đến Dim_Location
    Quantity            INTEGER NOT NULL,           -- Số lượng sản phẩm bán ra
    UnitPrice           DECIMAL(10, 2) NOT NULL,    -- Đơn giá bán thực tế
    TotalRevenue        DECIMAL(12, 2) NOT NULL,    -- Doanh thu dòng = Quantity * UnitPrice
    
    -- Ràng buộc khóa ngoại (Foreign Key Constraints)
    CONSTRAINT fk_sales_date FOREIGN KEY (DateKey) REFERENCES Dim_Date(DateKey),
    CONSTRAINT fk_sales_customer FOREIGN KEY (CustomerKey) REFERENCES Dim_Customer(CustomerKey),
    CONSTRAINT fk_sales_product FOREIGN KEY (ProductKey) REFERENCES Dim_Product(ProductKey),
    CONSTRAINT fk_sales_location FOREIGN KEY (LocationKey) REFERENCES Dim_Location(LocationKey)
);

-- ------------------------------------------------------------------------------
-- 6. TẠO CÁC CHỈ MỤC (INDEXES) TỐI ƯU HÓA TRUY VẤN OLAP
-- ------------------------------------------------------------------------------
CREATE INDEX idx_fact_date ON Fact_Sales(DateKey);
CREATE INDEX idx_fact_customer ON Fact_Sales(CustomerKey);
CREATE INDEX idx_fact_product ON Fact_Sales(ProductKey);
CREATE INDEX idx_fact_location ON Fact_Sales(LocationKey);
CREATE INDEX idx_fact_invoiceno ON Fact_Sales(InvoiceNo);

CREATE INDEX idx_dim_date_year_month ON Dim_Date(Year, Month);
CREATE INDEX idx_dim_customer_id ON Dim_Customer(CustomerID);
CREATE INDEX idx_dim_product_stockcode ON Dim_Product(StockCode);

-- ------------------------------------------------------------------------------
-- 7. BẢNG CHIỀU TỶ GIÁ TIỀN TỆ (Dim_Currency)  [Mở rộng – Nguồn: Frankfurter API / ECB]
-- Lưu trữ tỷ giá hối đoái GBP theo từng tháng để hỗ trợ phân tích đa tiền tệ.
-- Nguồn dữ liệu: https://api.frankfurter.app (European Central Bank Reference Rates)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS Dim_Currency;

CREATE TABLE Dim_Currency (
    CurrencyKey     INTEGER PRIMARY KEY,    -- Surrogate Key tự tăng
    Year            INTEGER NOT NULL,       -- Năm (ví dụ: 2011)
    Month           INTEGER NOT NULL,       -- Tháng (1 - 12)
    YearMonth       VARCHAR(7) NOT NULL,    -- Định dạng YYYY-MM (ví dụ: 2011-03)
    RateDate        DATE NOT NULL,          -- Ngày giao dịch cuối tháng (ngày thực tế có dữ liệu ECB)
    GBP_Base        DECIMAL(5,2) NOT NULL DEFAULT 1.00, -- Đồng tiền gốc (luôn = 1)
    USD_Rate        DECIMAL(10,6),          -- 1 GBP = x USD (tỷ giá ECB)
    EUR_Rate        DECIMAL(10,6),          -- 1 GBP = x EUR (tỷ giá ECB)
    API_Source      VARCHAR(100) NOT NULL DEFAULT 'Frankfurter API (ECB Reference Rates)',
    UNIQUE(Year, Month)
);

CREATE INDEX idx_currency_yearmonth ON Dim_Currency(YearMonth);
CREATE INDEX idx_currency_year_month ON Dim_Currency(Year, Month);
