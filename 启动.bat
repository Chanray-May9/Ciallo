@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist Ciallo.exe (
    start "" "Ciallo.exe"
    exit /b
)
if exist MineDeck.exe (
    start "" "MineDeck.exe"
    exit /b
)
python app.py
if errorlevel 1 (
    echo.
    echo 启动失败：请确认已安装 Python 3.11+ 与 PySide6
    pause
)
