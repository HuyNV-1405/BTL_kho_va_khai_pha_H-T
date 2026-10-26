# Kịch bản PowerShell chạy dự án chỉ với 1 câu lệnh
# Sử dụng: .\run.ps1
# Hoặc:    .\run.ps1 --skip-etl
# Hoặc:    .\run.ps1 --sqlite

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  KHO DỮ LIỆU BÁN LẺ & KHAI PHÁ DỮ LIỆU (ONE-COMMAND MASTER LAUNCHER)          " -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
}

python run_all.py @args
