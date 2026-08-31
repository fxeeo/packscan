@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".env" copy /Y ".env.example" ".env" >nul

if not exist "backend\.venv\Scripts\uvicorn.exe" (
  echo ERROR: Backend venv missing. Run setup.bat first.
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo ERROR: frontend\node_modules missing. Run setup.bat first.
  exit /b 1
)

set PACKSCAN_API_HOST=127.0.0.1
set PACKSCAN_API_PORT=8000
set PACKSCAN_OCR_ENGINE=paddle
set VITE_API_PROXY_TARGET=http://127.0.0.1:8000
set VITE_DEV_PORT=5173

echo Starting PackScan API on %PACKSCAN_API_HOST%:%PACKSCAN_API_PORT% ...
start "PackScan-API" cmd /k "cd /d ""%~dp0backend"" && call .venv\Scripts\activate.bat && set PACKSCAN_OCR_ENGINE=%PACKSCAN_OCR_ENGINE% && uvicorn main:app --host %PACKSCAN_API_HOST% --port %PACKSCAN_API_PORT% --reload"

timeout /t 4 /nobreak >nul

echo Starting PackScan UI on port %VITE_DEV_PORT% ...
start "PackScan-UI" cmd /k "cd /d ""%~dp0frontend"" && set VITE_API_PROXY_TARGET=%VITE_API_PROXY_TARGET% && npm run dev -- --host 0.0.0.0 --port %VITE_DEV_PORT%"

echo.
echo Open UI : http://127.0.0.1:%VITE_DEV_PORT%/
echo API docs: http://%PACKSCAN_API_HOST%:%PACKSCAN_API_PORT%/docs
echo Close the two opened windows to stop the app.
endlocal
