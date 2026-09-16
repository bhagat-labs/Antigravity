@echo off
title CampusBell - Daily Timetable Reminder App
echo =======================================================
echo   🎓 CampusBell - Daily Timetable Mobile Reminder App
echo =======================================================
echo Starting backend server and web dashboard...
echo.

set PYTHONIOENCODING=utf-8

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.9+.
    pause
    exit /b 1
)

:: Launch browser in background after 2 seconds
start "" powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"

:: Run FastAPI server with Uvicorn
python app.py

pause
