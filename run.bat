@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ==============================================================================
echo   KHO DỮ LIỆU BÁN LẺ VÀ KHAI PHÁ DỮ LIỆU (ONE-COMMAND MASTER LAUNCHER)
echo ==============================================================================

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python run_all.py %*
pause
