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

---

## 👥 HƯỚNG DẪN THÀNH VIÊN NHÓM CÀI ĐẶT VÀ CHẠY DỰ ÁN

### 1. Chuẩn bị

- Cài **Git** và **Python 3.10 trở lên**.
- Nếu cần chạy MinIO, PostgreSQL và Superset, cài thêm **Docker Desktop** và khởi động Docker.
- Clone repository về máy:

  ```powershell
  git clone https://github.com/fhgssg/BTL_kho_va_khai_pha_H-T.git
  cd BTL_kho_va_khai_pha_H-T
  ```

### 2. Tạo môi trường Python và cài thư viện

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell không cho phép kích hoạt môi trường, mở Command Prompt và chạy:

```bat
.\.venv\Scripts\activate.bat
```

### 3. Cung cấp dữ liệu nguồn

Các file dữ liệu CSV và database được loại khỏi Git để tránh đẩy các file lớn lên repository. Thành viên cần nhận file dữ liệu nguồn `data.csv` từ người quản lý dự án và đặt vào đúng vị trí:

```text
data\raw\data.csv
```

Nếu chưa có thư mục `data\raw`, hãy tạo thư mục đó trước khi chép file.

### 4. Tạo dữ liệu sạch, kho dữ liệu và kết quả phân tích

Chạy các lệnh từ thư mục gốc dự án, sau khi đã kích hoạt môi trường Python:

```powershell
python scripts\01_eda_and_cleaning.py
python scripts\03_etl_pipeline.py
python scripts\05_data_mining.py
```

Các script lần lượt tạo dữ liệu sạch, kho SQLite tại `database\retail_dwh.db`, và các kết quả khai phá tại thư mục `outputs`.

### 5. Chạy Dashboard

```powershell
python -m streamlit run app.py
```

Mở địa chỉ được Streamlit in trong terminal, thường là `http://localhost:8501`. Để dừng Dashboard, nhấn `Ctrl+C` trong terminal đang chạy.

### 6. (Tùy chọn) Chạy các dịch vụ Docker

Phần MinIO, PostgreSQL và Superset là hạ tầng mở rộng; không bắt buộc nếu chỉ chạy Dashboard dựa trên SQLite.

```powershell
docker compose up -d
python scripts\06_lakehouse_minio_postgres_etl.py
```

Để dừng các dịch vụ mà giữ dữ liệu trong Docker volumes:

```powershell
docker compose stop
```

Docker volumes nằm trên máy của từng thành viên và không được chia sẻ qua Git. Không chạy `docker compose down -v` nếu chưa sao lưu hoặc chưa chủ động muốn xóa dữ liệu volumes.
