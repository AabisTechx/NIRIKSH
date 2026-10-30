@echo off
title NIRIKSH — Institutional Approval & Compliance System (SIH 2026)
echo ============================================================================
echo   NIRIKSH — Institutional Approval ^& Compliance System (Team CODERED)
echo ============================================================================
echo.
echo Checking Python environment...
cd /d "%~dp0backend"

python -c "import fastapi, uvicorn, fitz" 2>nul
if %errorlevel% neq 0 (
    echo Installing required Python packages ^(FastAPI, Uvicorn, SQLAlchemy, PyMuPDF^)...
    pip install fastapi uvicorn sqlalchemy pydantic pymupdf python-multipart
)

echo.
echo Starting NIRIKSH Full-Stack Server ^(Frontend UI + FastAPI + SQLite^) on http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
