@echo off
title WiFi Audio Stream Launcher
setlocal enabledelayedexpansion

:: Jump to the folder where this bat file locates
cd /d "%~dp0"

:: Pre-check virtual environment python
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment python not found
    echo Make sure this bat file is placed inside wifiMusic folder with .venv directory
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:: Pre-check main program file
if not exist "main.py" (
    echo ERROR: Main program main.py missing
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Activating Python virtual environment...
call ".venv\Scripts\activate.bat"

echo.
echo Starting WiFi Hi-Res Audio Stream Service with HIGH process priority
echo =====================================================
:: start /HIGH : launch python with high CPU priority
:: "" = mandatory empty window title parameter for start command
:: /wait : block bat until python program exit
start "" /HIGH /wait python main.py
echo =====================================================
echo.
echo Program finished or crashed. Check error messages above.
echo Press any key to close window...
pause >nul