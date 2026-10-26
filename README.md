# ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ONLINE RETAIL DATA LAKEHOUSE & ANALYTICS)

Dự án nghiên cứu, thiết kế và hiện thực hóa kiến trúc **Hồ Dữ Liệu & Kho Dữ Liệu Hiện Đại (Modern Data Lakehouse)** kết hợp Phân tích kinh doanh và Trực quan hóa dữ liệu (Business Intelligence).

---

## 🌟 LUỒNG CHÍNH LAKEHOUSE (SYSTEM ARCHITECTURE)

```
[ data/raw/data.csv ] -> [ MinIO raw ] -> [ EDA & Cleaning ] -> [ MinIO staging ]
                                                                    ↓
                                                                curated
                                                                    ↓
                                                  [ PostgreSQL Star Schema DWH ]
                                                       ┌────────────┴──────────┐
                                                       ▼                       ▼
                                                 [ OLAP & Mining ]       [ Dashboards ]

SQLite là phương án local/dự phòng; không nằm trong luồng triển khai chính.
```

MinIO là Lakehouse bắt buộc, nơi dữ liệu đi qua các lớp raw, staging (Parquet) và
curated (Star Schema dạng Parquet). Pipeline chỉ nạp curated sang PostgreSQL sau khi
các đối tượng đã được ghi và đọc lại từ MinIO. OLAP, RFM, Apriori và Streamlit dùng
PostgreSQL làm nguồn chính. SQLite được giữ làm phương án local/dự phòng.

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
│   ├── raw/exchange_rates_raw.json  # Snapshot phản hồi API tỷ giá
│   └── processed/              # Dữ liệu sạch và dữ liệu bị loại kèm lý do
│
├── database/                   # Kho dữ liệu & Tài liệu thiết kế
│   ├── retail_dwh.db           # Kho SQLite dự phòng/local
│   ├── 02_schema_ddl.sql       # Kịch bản DDL Star Schema
│   └── 02_data_modeling.md     # Tài liệu thiết kế mô hình đa chiều Kimball
│
├── scripts/                    # Toàn bộ mã nguồn Python thực thi các giai đoạn
│   ├── 01_eda_and_cleaning.py  # Giai đoạn 1: EDA & Làm sạch dữ liệu
│   ├── 03_etl_pipeline.py      # ETL SQLite dự phòng/local
│   ├── 04_run_olap_queries.py  # Giai đoạn 4: Thực thi 8 truy vấn phân tích OLAP
│   ├── 05_data_mining.py       # Giai đoạn 5: RFM, K-Means & Market Basket
│   ├── 03b_dwh_test_reconciliation.py # Kiểm thử và đối soát kho
│   └── 06_lakehouse_minio_postgres_etl.py  # ETL chính: MinIO Lakehouse -> PostgreSQL
│
├── sql/                        # Kịch bản SQL phân tích
│   ├── 02_schema_ddl.sql       # DDL tạo Schema
│   └── 04_olap_queries.sql     # 8 bài toán truy vấn OLAP & SQL nâng cao
│
├── outputs/                    # Kết quả khai phá, dữ liệu tỷ giá và báo cáo audit/test
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

1. **Khởi động hạ tầng Lakehouse**:
   ```bash
   docker compose up -d
   ```
2. **Chạy ETL chính** — pipeline đưa dữ liệu gốc lên MinIO trước, sau đó đọc bản raw từ MinIO để làm sạch, tạo staging/curated và nạp vào PostgreSQL:
   ```bash
   python scripts\06_lakehouse_minio_postgres_etl.py
   ```
3. **Kiểm thử DWH, sau đó chạy OLAP và khai phá**:
   ```bash
   python scripts\03b_dwh_test_reconciliation.py
   python scripts\04_run_olap_queries.py
   python scripts\05_data_mining.py
   ```
4. **Mở Web Dashboard tương tác (Streamlit)**:
   ```bash
   python -m streamlit run app.py
   ```

---

## 👥 HƯỚNG DẪN THÀNH VIÊN NHÓM CÀI ĐẶT VÀ CHẠY DỰ ÁN

### 1. Chuẩn bị

- Cài **Git** và **Python 3.10 trở lên**.
- Cài **Docker Desktop** và khởi động Docker để chạy MinIO và PostgreSQL (bắt buộc cho luồng chính). Superset là tùy chọn.
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

### 4. Tạo dữ liệu sạch, nạp Lakehouse/DWH và phân tích

Chạy các lệnh từ thư mục gốc dự án, sau khi đã kích hoạt môi trường Python:

```powershell
python scripts\07_api_enrichment.py
docker compose up -d minio minio-init postgres
python scripts\06_lakehouse_minio_postgres_etl.py
python scripts\03b_dwh_test_reconciliation.py
python scripts\04_run_olap_queries.py
python scripts\05_data_mining.py
```

Script 06 đưa CSV gốc lên MinIO raw trước, tải bản raw đó để chạy EDA/làm sạch,
sau đó ghi dữ liệu sạch vào staging, tạo curated và nạp PostgreSQL. Các file CSV sạch,
bị loại và báo cáo audit vẫn được lưu cục bộ trong `data\processed` và `outputs`.
Script 01 có thể chạy độc lập để khảo sát/làm sạch thủ công, nhưng không cần chạy trước
pipeline chính. Script 07 là tùy chọn nếu cần bổ sung dữ liệu tỷ giá; nó lưu snapshot và
CSV để script 06 ingest vào Lakehouse.
Chỉ chạy kiểm thử, OLAP, khai phá và dashboard sau khi pipeline Lakehouse hoàn tất.

### 5. Chạy Dashboard

```powershell
python -m streamlit run app.py
```

Mở địa chỉ được Streamlit in trong terminal, thường là `http://localhost:8501`. Để dừng Dashboard, nhấn `Ctrl+C` trong terminal đang chạy.

### 6. Hạ tầng Lakehouse

MinIO và PostgreSQL là thành phần bắt buộc của luồng chính; Superset là giao diện BI tùy chọn.

```powershell
docker compose up -d
python scripts\06_lakehouse_minio_postgres_etl.py
```

SQLite được giữ làm phương án local/dự phòng. Để dùng SQLite cho các script phân tích,
đặt `DWH_DATABASE_URL=sqlite:///database/retail_dwh.db` và nạp riêng bằng
`python scripts\03_etl_pipeline.py`. Luồng SQLite bỏ qua Lakehouse nên không thay thế ETL chính.

Để dừng các dịch vụ mà giữ dữ liệu trong Docker volumes:

```powershell
docker compose stop
```

Docker volumes nằm trên máy của từng thành viên và không được chia sẻ qua Git. Không chạy `docker compose down -v` nếu chưa sao lưu hoặc chưa chủ động muốn xóa dữ liệu volumes.
