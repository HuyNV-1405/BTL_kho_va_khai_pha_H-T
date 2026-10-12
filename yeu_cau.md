# ĐỀ TÀI: XÂY DỰNG KHO DỮ LIỆU & PHÂN TÍCH KINH DOANH BÁN LẺ (ONLINE RETAIL DATA WAREHOUSE & ANALYTICS)

---

## 1. TỔNG QUAN ĐỀ TÀI
- **Tập dữ liệu nguồn**: `data.csv` (Online Retail Dataset - dữ liệu giao dịch thương mại điện tử thực tế của một doanh nghiệp bán lẻ quà lưu niệm trực tuyến có trụ sở tại Vương quốc Anh).
- **Quy mô dữ liệu**: ~540,000 dòng giao dịch, 8 thuộc tính chính (`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`).
- **Mục tiêu chính**:
  1. Xử lý và làm sạch dữ liệu giao dịch gốc.
  2. Thiết kế và hiện thực hóa mô hình **Kho Dữ Liệu (Data Warehouse)** chuẩn Star Schema / Snowflake Schema.
  3. Xây dựng đường ống trích xuất, biến đổi và nạp dữ liệu (**ETL Pipeline**).
  4. Thực hiện các phép phân tích đa chiều (**OLAP / Advanced SQL Analytics**).
  5. Áp dụng các thuật toán **Khai phá dữ liệu (Data Mining)**: Phân khúc khách hàng (RFM Model) và Phân tích giỏ hàng (Market Basket Analysis).
  6. Xây dựng **Dashboard trực quan hóa dữ liệu (Business Intelligence)** hỗ trợ ra quyết định.

---

## 2. YÊU CẦU CHI TIẾT THEO TỪNG PHẦN

### Yêu Cầu 1: Khám phá Dữ liệu & Tiền xử lý (EDA & Data Cleaning)
- **Đánh giá chất lượng dữ liệu**:
  - Tỷ lệ giá trị khuyết thiếu (Missing Values), đặc biệt tại cột `CustomerID` và `Description`.
  - Phân tích ngoại lai (Outliers) và giá trị bất thường: Số lượng âm (`Quantity < 0`), đơn giá âm hoặc bằng 0 (`UnitPrice <= 0`).
  - Phân loại đơn hàng hủy: Các hóa đơn bắt đầu bằng ký tự `'C'` (Cancellation).
- **Quy tắc làm sạch & chuẩn hóa**:
  - Loại bỏ hoặc tách riêng các đơn hàng hủy/trả hàng.
  - Chuẩn hóa định dạng ngày tháng (`InvoiceDate` sang chuẩn `YYYY-MM-DD HH:MM:SS`).
  - Chuẩn hóa chuỗi văn bản (`Description`: chữ in hoa, loại bỏ khoảng trắng thừa).
  - Điền giá trị hoặc xử lý các bản ghi khuyết thiếu phù hợp với nghiệp vụ.

---

### Yêu Cầu 2: Thiết kế Mô hình Kho Dữ Liệu (Dimensional Modeling)
- **Thiết kế mô hình hình sao (Star Schema)**:
  - **Fact Table**: `Fact_Sales` (hoặc `Fact_Orders`)
    - *Measures*: `Quantity`, `UnitPrice`, `TotalAmount` (Quantity * UnitPrice), `DiscountAmount`.
    - *Foreign Keys*: `DateKey`, `ProductKey`, `CustomerKey`, `LocationKey`.
  - **Dimension Tables**:
    - `Dim_Product`: `ProductKey` (Surrogate Key), `StockCode`, `Description`, `Category` (nếu có phân loại).
    - `Dim_Customer`: `CustomerKey` (Surrogate Key), `CustomerID` (Natural Key), `CustomerSegment`.
    - `Dim_Date`: `DateKey`, `FullDate`, `DayOfWeek`, `DayName`, `Month`, `Quarter`, `Year`, `IsWeekend`.
    - `Dim_Location`: `LocationKey`, `Country`.
- **Đầu ra yêu cầu**: Sơ đồ ERD / Dimensional Schema thể hiện rõ khóa chính (PK), khóa ngoại (FK), kiểu dữ liệu và ràng buộc.

---

### Yêu Cầu 3: Xây dựng Đường ống ETL (Extract - Transform - Load)
- **Extract**: Đọc dữ liệu từ file gốc `data.csv`.
- **Transform**:
  - Áp dụng các bộ lọc làm sạch ở Yêu cầu 1.
  - Tạo các khóa đại diện (Surrogate Keys) cho các bảng Dimension.
  - Tính toán các chỉ số phái sinh (ví dụ: `Revenue = Quantity * UnitPrice`).
  - Xử lý SCD (Slowly Changing Dimensions) nếu cần mở rộng theo dõi lịch sử khách hàng.
- **Load**:
  - Tự động tạo bảng và nạp dữ liệu vào cơ sở dữ liệu kho (SQLite / DuckDB / PostgreSQL / SQL Server).
  - Ghi log quá trình nạp: Số bản ghi trích xuất, số bản ghi lỗi, số bản ghi nạp thành công.

---

### Yêu Cầu 4: Truy vấn Phân tích Đa chiều (OLAP & SQL Analytics)
Hiện thực các truy vấn SQL / OLAP trả lời các bài toán kinh doanh cốt lõi:
1. **Phân tích Doanh thu theo Thời gian**: Doanh thu theo năm, quý, tháng, ngày trong tuần, khung giờ vàng mua sắm.
2. **Top Sản phẩm chủ lực**: Top 10 sản phẩm bán chạy nhất về số lượng và mang lại doanh thu cao nhất.
3. **Phân tích Thị trường Địa lý**: Doanh thu và số lượng đơn hàng theo từng quốc gia (UK so với các thị trường quốc tế).
4. **Hành vi Khách hàng**: Tỷ lệ khách hàng quay lại mua hàng (Repeat Customer Rate), giá trị đơn hàng trung bình (AOV - Average Order Value).
5. **Thao tác OLAP**: Sử dụng các mệnh đề nâng cao như `GROUP BY ROLLUP`, `CUBE`, `GROUPING SETS`, và `Window Functions` (RANK, DENSE_RANK, LAG, LEAD, RUNNING TOTAL).

---

### Yêu Cầu 5: Khai phá Dữ liệu Chuyên sâu (Data Mining & Machine Learning)
1. **Phân khúc khách hàng theo mô hình RFM (Recency - Frequency - Monetary)**:
   - *Recency (R)*: Số ngày kể từ lần mua hàng gần nhất đến thời điểm phân tích.
   - *Frequency (F)*: Tổng số đơn hàng đã đặt.
   - *Monetary (M)*: Tổng số tiền khách hàng đã chi tiêu.
   - Chấm điểm RFM (1-5) và gán nhãn: *Champions, Loyal Customers, Potential Loyalists, At Risk, Lost*.
   - *(Mở rộng)* Áp dụng thuật toán gom cụm **K-Means Clustering** để đối chiếu với phân cụm thủ công.
2. **Phân tích Giỏ hàng (Market Basket Analysis)**:
   - Sử dụng thuật toán **Apriori** hoặc **FP-Growth** tìm tập phổ biến và luật kết hợp (Association Rules).
   - Đo lường qua các chỉ số: *Support*, *Confidence*, *Lift*.
   - Đưa ra đề xuất gợi ý bán chéo (Cross-selling / Bundle Recommendations).

---

### Yêu Cầu 6: Trực quan hóa Dữ liệu (Dashboard & Báo cáo)
- Xây dựng Dashboard tương tác (qua **Streamlit** bằng Python hoặc **Power BI**):
  - **Trang 1 - Overview Executive**: Các thẻ chỉ số chính (KPIs: Tổng doanh thu, Tổng đơn hàng, Số khách hàng, AOV), biểu đồ xu hướng doanh thu theo thời gian.
  - **Trang 2 - Phân tích Sản phẩm & Khu vực**: Bản đồ doanh số theo quốc gia, cơ cấu danh mục mặt hàng.
  - **Trang 3 - Chân dung & Phân khúc Khách hàng**: Biểu đồ phân bổ nhóm RFM, danh sách khách hàng VIP.
  - **Trang 4 - Gợi ý Bán hàng (Product Recommendation)**: Xem các cặp sản phẩm thường mua cùng nhau.

---

## 3. SẢN PHẨM ĐẦU RA BÀN GIAO (DELIVERABLES)
1. Mã nguồn Python làm sạch dữ liệu, ETL và mô hình hóa (`etl_pipeline.py` hoặc Jupyter Notebook `EDA_and_ETL.ipynb`).
2. Tệp cơ sở dữ liệu Kho dữ liệu đã nạp đầy đủ (Database file hoặc file SQL dump).
3. Tập hợp các câu truy vấn SQL phân tích nghiệp vụ (`olap_queries.sql`).
4. Script khai phá dữ liệu RFM & Market Basket Analysis (`data_mining.py`).
5. Ứng dụng Dashboard tương tác (`app.py` chạy bằng Streamlit) hoặc file báo cáo Power BI (`.pbix`).
6. Báo cáo tổng kết đồ án (Báo cáo Word/PDF và slide thuyết trình).
