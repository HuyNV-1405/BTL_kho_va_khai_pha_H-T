# ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ONLINE RETAIL DATA LAKEHOUSE & ANALYTICS)

Dự án nghiên cứu, thiết kế và hiện thực hóa kiến trúc **Hồ Dữ Liệu & Kho Dữ Liệu Hiện Đại (Modern Data Lakehouse)** kết hợp Phân tích kinh doanh và Trực quan hóa dữ liệu (Business Intelligence).

---

## 🌟 KIẾN TRÚC HỆ THỐNG HIỆN TẠI (SYSTEM ARCHITECTURE)

```
[ Dữ liệu thô CSV ]
        │
        ▼
[ MinIO S3 Lakehouse ] ──► Tầng raw/ (Raw Data)
        │
        ├──► DuckDB / PyArrow ──► Tầng staging/ (Parquet nén)
        │
        └──► Dimensional Model ──► Tầng curated/ (Star Schema Parquet)
                                         │
                                         ▼
                            [ PostgreSQL DWH (localhost:5432) ]
                            (dim_date, dim_location, dim_customer, dim_product, fact_sales)
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
         [ Apache Superset BI ]                     [ Streamlit Dashboard ]
         (http://localhost:8088)                     (http://localhost:8501)
```

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN (PROJECT STRUCTURE)

```
E:\ổ D\Kho\B\
│
├── docker-compose.yml          # Hạ tầng Container: MinIO + PostgreSQL + Apache Superset
├── requirements.txt            # Danh sách thư viện Python cần thiết
│
├── data/                       # Dữ liệu phục vụ hệ thống
│   ├── raw/data.csv            # Dữ liệu giao dịch thô ban đầu
│   └── processed/data_cleaned.csv  # Dữ liệu sạch đã tiền xử lý
│
├── database/                   # Kho dữ liệu & Tài liệu thiết kế
│   ├── retail_dwh.db           # Cơ sở dữ liệu SQLite Data Warehouse dự phòng
│   ├── 02_schema_ddl.sql       # Kịch bản DDL Star Schema
│   └── 02_data_modeling.md     # Tài liệu thiết kế mô hình đa chiều Kimball
│
├── scripts/                    # Toàn bộ mã nguồn Python thực thi các giai đoạn
│   ├── 01_eda_and_cleaning.py  # Giai đoạn 1: EDA & Làm sạch dữ liệu
│   ├── 03_etl_pipeline.py      # Giai đoạn 3: ETL Pipeline nạp vào SQLite
│   ├── 04_run_olap_queries.py  # Giai đoạn 4: Thực thi 8 truy vấn phân tích OLAP
│   ├── 05_data_mining.py       # Giai đoạn 5: Khai phá dữ liệu RFM & Phân tích giỏ hàng
│   └── 06_lakehouse_minio_postgres_etl.py  # Data Lakehouse: MinIO S3 & PostgreSQL DWH
│
├── sql/                        # Kịch bản SQL phân tích
│   ├── 02_schema_ddl.sql       # DDL tạo Schema
│   └── 04_olap_queries.sql     # 8 bài toán truy vấn OLAP & SQL nâng cao
│
├── outputs/                    # Kết quả xuất ra từ mô hình phân tích & khai phá dữ liệu
│   ├── rfm_customer_segments.csv   # Kết quả phân khúc khách hàng RFM & K-Means
│   └── market_basket_rules.csv     # 992 luật kết hợp gợi ý bán chéo (Apriori)
│
├── app.py                      # Ứng dụng Web Dashboard tương tác (Streamlit)
├── BAO_CAO_DO_AN.md            # Báo cáo tổng kết đồ án chi tiết (Word/Markdown)
├── lo_trinh.md                 # Lộ trình tổng thể và trạng thái hoàn thành từng giai đoạn
├── yeu_cau.md                  # Đề bài gốc ban đầu
├── yeu_cau_moi.md              # Yêu cầu hạ tầng Container mới (Docker, MinIO, Postgres)
└── README.md                   # Hướng dẫn tổng quan và khởi chạy hệ thống
```

---

## 🚀 THÔNG TIN DỊCH VỤ & CỔNG TRUY CẬP (SERVICES DIRECTORY)

| Dịch vụ | Địa chỉ Web / Endpoint | Tài khoản truy cập | Mô tả |
|---|---|---|---|
| **MinIO Console** | `http://localhost:9001` | `minioadmin` / `minioadmin123` | Giao diện quản lý Hồ dữ liệu S3 (Buckets: `raw`, `staging`, `curated`) |
| **MinIO API (S3)** | `http://localhost:9000` | `minioadmin` / `minioadmin123` | S3 Endpoint dùng trong code Python / DuckDB |
| **PostgreSQL DWH** | `localhost:5432` | `dataeng` / `dataeng123` (DB: `dwh`) | Cơ sở dữ liệu Kho Dữ Liệu chuẩn Star Schema |
| **Apache Superset** | `http://localhost:8088` | `admin` / `admin` | Nền tảng Business Intelligence chuyên nghiệp |
| **Streamlit Dashboard**| `http://localhost:8501` | Truy cập trực tiếp | Dashboard tương tác tùy biến với công cụ gợi ý bán chéo |

---

## 🛠️ HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG

1. **Khởi động hạ tầng Docker**:
   ```bash
   docker compose up -d
   ```
2. **Chạy đường ống nạp dữ liệu Lakehouse (MinIO S3 & PostgreSQL)**:
   ```bash
   python scripts/06_lakehouse_minio_postgres_etl.py
   ```
3. **Chạy mô hình khai phá dữ liệu RFM & Phân tích giỏ hàng**:
   ```bash
   python scripts/05_data_mining.py
   ```
4. **Mở Web Dashboard tương tác (Streamlit)**:
   ```bash
   python -m streamlit run app.py
   ```
