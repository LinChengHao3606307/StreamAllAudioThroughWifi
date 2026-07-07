@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo =====================================================
echo WiFi Music One-Click Setup
echo =====================================================

echo.
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )

    if errorlevel 1 (
        echo Failed to create virtual environment.
        echo Please install Python 3 and ensure the "py" command is available.
        pause >nul
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause >nul
    exit /b 1
)

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause >nul
    exit /b 1
)

echo.
echo Running VB-Cable installer...
python install_vbcable.py

echo.
echo Setup completed.
echo If you want to start the app later, run runWifiMusic.bat

echo Press any key to exit...
pause >nul
