@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  PackScan SETUP (Windows)
echo ========================================

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo Created .env from .env.example
) else (
  echo .env already exists — keeping it
)

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found in PATH. Install Python 3.10-3.12 x64 first.
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found in PATH. Install Node.js 20+ LTS first.
  exit /b 1
)

echo.
echo [1/4] Creating Python venv...
cd backend
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo [2/4] Installing backend requirements (PaddleOCR can take several minutes)...
pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
  exit /b 1
)

echo [3/4] Initializing database folders...
python scripts\init_db.py

cd ..\frontend
echo [4/4] Installing frontend npm packages...
call npm install
if errorlevel 1 (
  echo ERROR: npm install failed.
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
)

cd ..
echo.
echo SETUP COMPLETE.
echo Next: run start.bat
echo UI will be http://127.0.0.1:5173
echo API docs http://127.0.0.1:8000/docs
endlocal
