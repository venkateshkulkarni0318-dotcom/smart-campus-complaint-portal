@echo off
TITLE Smart Campus Portal - Web Server
echo ============================================================
echo   SMART CAMPUS COMPLAINT & MAINTENANCE PORTAL
echo   Environment: Python Flask + MySQL 8.0 + Bootstrap 5
echo ============================================================
echo.
echo Checking Python virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not detected!
    echo Please run 'python -m venv venv' and install requirements.
    pause
    exit /b 1
)

echo Starting application server on http://127.0.0.1:5000 ...
echo Press Ctrl+C in this console window to stop the server.
echo.
.\venv\Scripts\python.exe app.py
pause
