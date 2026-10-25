"""
Script 07: API Enrichment – Currency Exchange Rate (Frankfurter API / ECB)
==========================================================================
GIAI ĐOẠN 1  – EDA: Kiểm tra & chuẩn hóa dữ liệu tỷ giá từ API
GIAI ĐOẠN 2  – Xuất snapshot raw và CSV staging cho Lakehouse pipeline

scripts/06_lakehouse_minio_postgres_etl.py đưa tỷ giá vào MinIO và PostgreSQL.
Truy vấn phân tích tỷ giá chạy sau đó qua scripts/04_run_olap_queries.py.

Nguồn API: https://api.frankfurter.app (ECB reference rates – miễn phí, không cần key)
"""
import os
import json
from datetime import datetime
import requests
import pandas as pd

# ─── CẤU HÌNH ────────────────────────────────────────────────────────────────
BASE_URL        = "https://api.frankfurter.app"
BASE_CURRENCY   = "GBP"
TARGET_CURR     = "USD,EUR"

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR         = os.path.join(BASE_DIR, "data", "raw")
RAW_SNAPSHOT    = os.path.join(RAW_DIR, "exchange_rates_raw.json")
OUTPUT_CSV      = os.path.join(BASE_DIR, "outputs", "exchange_rates.csv")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# GIAI ĐOẠN 1: EDA & INGESTION – Trích xuất, lưu raw snapshot & kiểm tra dữ liệu API
# ─────────────────────────────────────────────────────────────────────────────
def fetch_and_validate() -> pd.DataFrame:
    print("\n" + "="*60)
    print("  GĐ 1 – INGESTION & EDA: Trích xuất tỷ giá từ Frankfurter API (ECB)")
    print("="*60)

    extracted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    is_fallback = False
    raw_response_data = None
    records = []

    try:
        url = f"{BASE_URL}/2010-12-01..2011-12-31"
        resp = requests.get(url, params={"from": BASE_CURRENCY, "to": TARGET_CURR}, timeout=15)
        resp.raise_for_status()
        raw_response_data = resp.json()
        print(f"✅ API trả về {len(raw_response_data.get('rates', {}))} ngày giao dịch.")
        print(f"   Base currency: {raw_response_data['base']} | Khoảng thời gian: {raw_response_data['start_date']} → {raw_response_data['end_date']}")

        for date_str, rates in raw_response_data["rates"].items():
            records.append({
                "RateDate": date_str,
                "USD_Rate": rates.get("USD"),
                "EUR_Rate": rates.get("EUR"),
            })
        df = pd.DataFrame(records)
    except Exception as e:
        is_fallback = True
        print(f"⚠️  API không khả dụng: {e}")
        print("   → Dùng fallback data (tỷ giá ước lượng ECB 2010-2011)")
        import numpy as np; np.random.seed(42)
        months = pd.date_range("2010-12", "2011-12", freq="MS")
        records = []
        for m in months:
            records.append({
                "RateDate": m.strftime("%Y-%m-%d"),
                "USD_Rate": round(float(np.random.uniform(1.54, 1.67)), 4),
                "EUR_Rate": round(float(np.random.uniform(1.13, 1.24)), 4),
            })
        df = pd.DataFrame(records)
        raw_response_data = {"rates": {r["RateDate"]: {"USD": r["USD_Rate"], "EUR": r["EUR_Rate"]} for r in records}}

    # Lưu snapshot thô (Raw Data Snapshot) kèm metadata nguồn gốc
    raw_snapshot = {
        "metadata": {
            "extracted_at": extracted_at,
            "endpoint": f"{BASE_URL}/2010-12-01..2011-12-31",
            "base_currency": BASE_CURRENCY,
            "target_currencies": TARGET_CURR,
            "status": "FALLBACK" if is_fallback else "SUCCESS",
            "is_fallback": is_fallback,
            "source": "Estimated ECB Benchmark (Offline Fallback)" if is_fallback else "European Central Bank via Frankfurter API",
            "record_count": len(records)
        },
        "payload": raw_response_data
    }
    with open(RAW_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(raw_snapshot, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu Raw API Snapshot kèm metadata tại: '{RAW_SNAPSHOT}'")

    df["RateDate"] = pd.to_datetime(df["RateDate"])
    df["Year"]  = df["RateDate"].dt.year
    df["Month"] = df["RateDate"].dt.month

    # Lấy tỷ giá đại diện của mỗi tháng = ngày cuối cùng có dữ liệu
    df_monthly = (
        df.sort_values("RateDate")
          .groupby(["Year", "Month"])
          .last()
          .reset_index()
    )
    df_monthly["YearMonth"]    = df_monthly["Year"].astype(str) + "-" + df_monthly["Month"].astype(str).str.zfill(2)
    df_monthly["GBP_Base"]     = 1.0
    df_monthly["CurrencyKey"]  = range(1, len(df_monthly) + 1)
    df_monthly["API_Source"]   = "Estimated ECB Benchmark (Fallback)" if is_fallback else "Frankfurter API (ECB Reference Rates)"
    df_monthly["Is_Fallback"]  = 1 if is_fallback else 0
    df_monthly["Extracted_At"] = extracted_at

    # ── Kiểm tra chất lượng dữ liệu ─────────────────────────────────────────
    print(f"\n📊 EDA – Kiểm tra chất lượng dữ liệu tỷ giá:")
    print(f"   Số tháng tỷ giá: {len(df_monthly)}")
    print(f"   Trạng thái nguồn: {'Dữ liệu dự phòng (FALLBACK)' if is_fallback else 'Dữ liệu thực từ ECB (LIVE)'}")
    print(f"   Missing USD_Rate: {df_monthly['USD_Rate'].isna().sum()}")
    print(f"   Missing EUR_Rate: {df_monthly['EUR_Rate'].isna().sum()}")
    print(f"   USD_Rate  – min: {df_monthly['USD_Rate'].min():.4f}, max: {df_monthly['USD_Rate'].max():.4f}, mean: {df_monthly['USD_Rate'].mean():.4f}")
    print(f"   EUR_Rate  – min: {df_monthly['EUR_Rate'].min():.4f}, max: {df_monthly['EUR_Rate'].max():.4f}, mean: {df_monthly['EUR_Rate'].mean():.4f}")
    print(f"\n{df_monthly[['YearMonth', 'USD_Rate', 'EUR_Rate', 'Is_Fallback']].to_string(index=False)}")
    return df_monthly


# ─────────────────────────────────────────────────────────────────────────────
# GIAI ĐOẠN 2: LƯU ĐẦU RA ĐỂ LAKEHOUSE PIPELINE INGEST
# ─────────────────────────────────────────────────────────────────────────────
def save_exchange_rates(df: pd.DataFrame):
    print("\n" + "="*60)
    print("  GĐ 2 – Lưu dữ liệu tỷ giá để Lakehouse ingest")
    print("="*60)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"💾 Đã lưu {len(df)} bản ghi tỷ giá → {OUTPUT_CSV}")
    print("   → Script 06 sẽ nạp CSV qua MinIO staging/curated vào PostgreSQL.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "★"*60)
    print("  SCRIPT 07 – API ENRICHMENT (Frankfurter / ECB)")
    print("  Trích xuất và kiểm tra tỷ giá; bước Lakehouse ETL chạy ở script 06")
    print("★"*60)

    df_rates = fetch_and_validate()       # GĐ 1
    save_exchange_rates(df_rates)

    print("\n" + "★"*60)
    print("  ✅ Tỷ giá sẵn sàng để ingest qua Lakehouse pipeline.")
    print("★"*60)
