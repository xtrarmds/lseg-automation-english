@echo off
chcp 65001 >nul
title LSEG Automation Program

echo ========================================
echo    LSEG Automation Program Startup
echo ========================================
echo.

:: Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo 💡 Please install Python 3.7+ and add it to PATH
    echo 💡 Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✅ Python found

:: Check if virtual environment exists
echo.
echo [2/5] Checking virtual environment...
if not exist ".venv" (
    echo ⚠️ Virtual environment not found, creating...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment found
)

:: Activate virtual environment and install dependencies
echo.
echo [3/5] Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install required packages (skip pip upgrade to avoid proxy issues)
echo Installing required packages...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    echo 💡 Please check requirements.txt file
    pause
    exit /b 1
)
echo ✅ Dependencies installed successfully

:: Check configuration file
echo.
echo [4/5] Checking configuration file...
if not exist "config.cnf" (
    echo ❌ Configuration file config.cnf not found
    echo 💡 Please create config.cnf file with proper settings
    pause
    exit /b 1
)
echo ✅ Configuration file found

:: Create necessary directories
echo.
echo [5/5] Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "downloads" mkdir downloads
if not exist "target" mkdir target
if not exist "drivers" mkdir drivers
echo ✅ Directories created/verified

:: Check Chrome driver
echo.
echo Checking Chrome driver...
if not exist "drivers\chromedriver.exe" (
    echo ⚠️ Chrome driver not found in drivers folder
    echo 💡 Selenium will attempt to download automatically
    echo 💡 For manual installation, download from: https://chromedriver.chromium.org/
) else (
    echo ✅ Chrome driver found
)

echo.
echo ========================================
echo    Starting LSEG Automation Program
echo ========================================
echo.

:: Run the automation program
echo 🚀 Starting automation program...
python lseg_login_english.py

:: Check program exit code
if errorlevel 1 (
    echo.
    echo ❌ Program execution failed
    echo 💡 Check logs for detailed error information
) else (
    echo.
    echo ✅ Program execution completed
)

echo.
echo Press any key to exit...
pause >nul 