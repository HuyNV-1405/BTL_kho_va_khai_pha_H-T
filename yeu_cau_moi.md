# 00 · PREREQUISITE — Cài đặt & Kiểm tra môi trường thực hành

## Cần cài (theo thứ tự)
1. **Docker Desktop** — nền tảng chạy MinIO + Postgres + Superset
2. Chạy `docker compose up -d` để bật hạ tầng
3. **Python 3.10+** và thư viện trong `requirements.txt`

## 0. Yêu cầu tối thiểu

| Hạng mục | Tối thiểu | Khuyến nghị |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Đĩa trống | 10 GB | 20 GB |
| CPU | 4 nhân, có ảo hoá (VT-x/AMD-V) | 8 nhân |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ | Windows 11 |

**Bật ảo hoá:** Task Manager → Performance → CPU → *Virtualization: Enabled*. Nếu `Disabled`, vào BIOS bật *Intel VT-x* / *SVM Mode*.
# 🔎 Thông tin máy
import platform, shutil, os
print("OS      :", platform.platform())
print("CPU     :", platform.processor() or platform.machine())
print("Python  :", platform.python_version())
total, used, free = shutil.disk_usage(os.getcwd())
print(f"Đĩa trống: {free/1e9:.1f} GB")
## 1. Cài Docker Desktop (bắt buộc)

Toàn bộ MinIO + Postgres + Superset chạy trong Docker.

**Windows 11:**
1. Mở PowerShell (Admin): `wsl --install` → khởi động lại máy.
2. Tải & cài **Docker Desktop**: https://www.docker.com/products/docker-desktop/ (giữ tuỳ chọn *Use WSL 2*).
3. Mở Docker Desktop, chờ biểu tượng cá voi **xanh**.

**macOS:** tải Docker Desktop đúng chip (Apple Silicon/Intel). **Linux:** `curl -fsSL https://get.docker.com | sh`.
# 🔎 Kiểm tra Docker đã cài & đang chạy
import subprocess, shutil
def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return None
if shutil.which("docker") is None:
    print("❌ Chưa tìm thấy 'docker'. Hãy cài Docker Desktop và mở nó lên.")
else:
    v = run(["docker","--version"]);  print("✅ Docker:", v.stdout.strip() if v else "?")
    info = run(["docker","info"])
    if info and info.returncode==0: print("✅ Docker Engine đang chạy.")
    else: print("❌ Docker chưa chạy — hãy MỞ Docker Desktop và chờ Engine xanh.")
## 2. Khởi động hạ tầng

Mở terminal trong thư mục `ThucHanh/` (chứa `docker-compose.yml`) và chạy:

```bash
docker compose up -d
```

Chờ vài phút (lần đầu tải image). Các dịch vụ & tài khoản:

| Dịch vụ | Địa chỉ | Tài khoản |
|---|---|---|
| MinIO Console | http://localhost:9001 | `minioadmin` / `minioadmin123` |
| MinIO API (S3) | http://localhost:9000 | (dùng trong code) |
| PostgreSQL | `localhost:5432` | `dataeng` / `dataeng123` |
| Superset (BI) | http://localhost:8088 | `admin` / `admin` |

> Ô dưới có thể **tự chạy** `docker compose up -d` giúp bạn (bỏ comment). Cần đứng đúng thư mục ThucHanh.
# (tuỳ chọn) Tự khởi động hạ tầng — bỏ comment 2 dòng dưới nếu muốn chạy từ notebook
# import subprocess
# print(subprocess.run(["docker","compose","up","-d"], capture_output=True, text=True).stdout)

# 🔎 Kiểm tra container đang chạy
import subprocess, shutil
if shutil.which("docker"):
    r = subprocess.run(["docker","compose","ps"], capture_output=True, text=True)
    print(r.stdout or r.stderr)
    print("→ Tất cả STATUS nên là 'running'/'healthy'. Nếu trống: chạy 'docker compose up -d' trong thư mục ThucHanh.")
## 3. Làm quen MinIO Console (Hồ dữ liệu)

1. Mở http://localhost:9001 → đăng nhập `minioadmin` / `minioadmin123`.
2. Vào **Buckets** — thấy sẵn `raw`, `staging`, `curated` (do dịch vụ `minio-init` tạo).
3. **Object Browser** để xem file sau khi notebook ghi dữ liệu.

> MinIO tương thích **chuẩn S3 (AWS)**. Code kết nối tới `http://localhost:9000` bằng khoá `minioadmin`/`minioadmin123` (đóng vai access key / secret key).
## 4. Cài Python & thư viện

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> Windows báo *"running scripts is disabled"* → chạy 1 lần:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

Sau đó `jupyter lab` (hoặc mở `.ipynb` bằng VS Code) và **chọn kernel `.venv`**.
# 🔎 Kiểm tra thư viện Python bắt buộc
import importlib
libs = ["duckdb","pandas","pyarrow","s3fs","sqlalchemy","psycopg2","sklearn","matplotlib","requests"]
missing=[]
for m in libs:
    try:
        importlib.import_module(m); print(f"✅ {m}")
    except Exception:
        missing.append(m); print(f"❌ {m}  (thiếu)")
if missing:
    print("\n→ Cài bổ sung:  pip install -r requirements.txt")
else:
    print("\n✅ Đủ thư viện.")
## 5. (Tuỳ chọn) Cài MinIO / Postgres ngoài Docker

Chỉ dùng khi **không dùng Docker**. Đa số bỏ qua mục này.

**MinIO server (Windows):**
```powershell
curl.exe -O https://dl.min.io/server/minio/release/windows-amd64/minio.exe
$env:MINIO_ROOT_USER="minioadmin"; $env:MINIO_ROOT_PASSWORD="minioadmin123"
.\minio.exe server .\minio-data --console-address ":9001"
```
**MinIO Client `mc`:**
```powershell
curl.exe -O https://dl.min.io/client/mc/release/windows-amd64/mc.exe
.\mc.exe alias set local http://localhost:9000 minioadmin minioadmin123
.\mc.exe mb local/raw local/staging local/curated
```
**PostgreSQL:** tải từ https://www.postgresql.org/download/ → tạo user `dataeng`/`dataeng123`, DB `dwh`, rồi `psql -U dataeng -d dwh -f init-source.sql`.
## 6. ✅ KIỂM TRA TỔNG THỂ (chạy ô này để xác nhận sẵn sàng)

Ô dưới kiểm tra kết nối thực tới **MinIO** và **PostgreSQL** rồi in bảng checklist.
# ✅ KIỂM TRA SẴN SÀNG THỰC HÀNH
CFG = {"s3_endpoint":"localhost:9000","s3_key":"minioadmin","s3_secret":"minioadmin123",
       "pg_dwh":"postgresql+psycopg2://dataeng:dataeng123@localhost:5432/dwh"}
result = {}

# 1) MinIO
try:
    import s3fs
    fs = s3fs.S3FileSystem(key=CFG["s3_key"], secret=CFG["s3_secret"],
                           client_kwargs={"endpoint_url":"http://"+CFG["s3_endpoint"]})
    buckets = [b.split("/")[0] for b in fs.ls("")]
    have = [b for b in ["raw","staging","curated"] if b in buckets]
    result["MinIO (:9000)"] = ("✅", f"bucket: {have or 'chưa có → tạo raw/staging/curated'}")
except Exception as e:
    result["MinIO (:9000)"] = ("❌", str(e)[:70])

# 2) Postgres
try:
    from sqlalchemy import create_engine, text
    with create_engine(CFG["pg_dwh"]).connect() as con:
        con.execute(text("select 1"))
    result["PostgreSQL (:5432)"] = ("✅", "kết nối OK")
except Exception as e:
    result["PostgreSQL (:5432)"] = ("❌", str(e)[:70])

# 3) DuckDB + httpfs
try:
    import duckdb
    d = duckdb.connect(); d.execute("INSTALL httpfs; LOAD httpfs;")
    result["DuckDB + httpfs"] = ("✅", duckdb.__version__)
except Exception as e:
    result["DuckDB + httpfs"] = ("❌", str(e)[:70])

# 4) Superset (cổng mở?)
import socket
def port_open(host, port):
    s=socket.socket(); s.settimeout(2)
    try: s.connect((host,port)); return True
    except Exception: return False
    finally: s.close()
result["Superset (:8088)"] = ("✅","cổng mở") if port_open("localhost",8088) else ("⚠️","chưa mở (chờ init hoặc chưa bật)")

print("="*56)
for k,(icon,msg) in result.items():
    print(f"{icon}  {k:<22} {msg}")
print("="*56)
ok = all(v[0]=="✅" for k,v in result.items() if k!="Superset (:8088)")
print("\n🎉 SẴN SÀNG! Mở Bai1_LamQuen_Ingestion.ipynb" if ok
      else "\n⚠️ Còn mục ❌ — xem Mục 7 Troubleshooting bên dưới.")
## 7. Khắc phục sự cố (Troubleshooting)

| Triệu chứng | Xử lý |
|---|---|
| `docker: command not found` | Mở Docker Desktop, chờ Engine xanh. |
| `port is already allocated` | Cổng bị chiếm → đổi cổng trái trong `docker-compose.yml` (vd `"5433:5432"`) & sửa `CFG`. |
| Superset :8088 lỗi 500 | Chưa init xong, chờ 1–2 phút. Log: `docker compose logs -f superset`. |
| `Connection refused` MinIO/Postgres | Container chưa chạy (`docker compose ps`) hoặc sai `CFG`. |
| `Access Denied` khi ghi MinIO | Sai key/secret — dùng `minioadmin`/`minioadmin123`. |
| Windows: venv activate bị chặn | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| Tải NYC Taxi chậm (Bài 1) | Tải `.parquet` trước, gán vào `CFG["taxi_local"]`. |
| Reset toàn bộ | `docker compose down -v` rồi `docker compose up -d` (⚠️ xoá dữ liệu). |

**Lệnh Docker hữu ích:**
```bash
docker compose ps
docker compose logs -f superset
docker compose stop     # tạm dừng, giữ dữ liệu
docker compose down -v  # xoá cả dữ liệu (reset)
```

---
