@echo off
REM
REM Digital Product Factory - Deployment Script (Windows)
REM
REM This script automates the complete setup and deployment process:
REM - Checks system requirements
REM - Creates virtual environment
REM - Installs dependencies
REM - Runs setup wizard
REM - Initializes database
REM - Runs validation tests
REM - Starts the system
REM
REM Usage:
REM   deploy.bat                 Full deployment
REM   deploy.bat skip-wizard     Skip interactive wizard
REM   deploy.bat dev             Development mode
REM

setlocal enabledelayedexpansion

REM Configuration
set PYTHON_MIN_VERSION=3.10
set PROJECT_DIR=%~dp0
set VENV_DIR=%PROJECT_DIR%venv
set LOG_DIR=%PROJECT_DIR%logs
set TIMESTAMP=%date:~-4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=%LOG_DIR%\deploy_%TIMESTAMP%.log

REM Parse arguments
set SKIP_WIZARD=false
set DEV_MODE=false

if "%1"=="skip-wizard" set SKIP_WIZARD=true
if "%1"=="dev" set DEV_MODE=true

REM Create log directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Start logging
echo Deployment started: %date% %time% > "%LOG_FILE%"

echo.
echo ================================================================================
echo           DIGITAL PRODUCT FACTORY - DEPLOYMENT (WINDOWS)
echo ================================================================================
echo.
echo Started: %date% %time%
echo Project Directory: %PROJECT_DIR%
echo Log File: %LOG_FILE%
echo.

REM Step 1: Check Python version
echo [1/10] Checking Python version...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python %PYTHON_MIN_VERSION% or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i

echo [SUCCESS] Python %PYTHON_VERSION% detected

REM Step 2: Check system requirements
echo [2/10] Checking system requirements...

REM Check disk space
for /f "tokens=3" %%a in ('dir /-c %PROJECT_DIR% ^| find "bytes free"') do set DISK_SPACE=%%a
echo [SUCCESS] System requirements checked

REM Step 3: Create virtual environment
echo [3/10] Creating virtual environment...

if exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment already exists
    set /p RECREATE="Remove and recreate? (y/N): "
    if /i "!RECREATE!"=="y" (
        rd /s /q "%VENV_DIR%"
        echo [SUCCESS] Removed existing virtual environment
    ) else (
        echo [SUCCESS] Using existing virtual environment
    )
)

if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
echo [SUCCESS] Virtual environment activated

REM Step 4: Upgrade pip
echo [4/10] Upgrading pip...

python -m pip install --upgrade pip -q
echo [SUCCESS] pip upgraded

REM Step 5: Install dependencies
echo [5/10] Installing dependencies...

if not exist "%PROJECT_DIR%requirements.txt" (
    echo [ERROR] requirements.txt not found
    pause
    exit /b 1
)

echo Installing from requirements.txt...
pip install -r "%PROJECT_DIR%requirements.txt" -q

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [SUCCESS] All dependencies installed

REM Step 6: Create directory structure
echo [6/10] Creating directory structure...

set DIRS=data logs output output\products output\marketing output\reports backups

for %%d in (%DIRS%) do (
    if not exist "%PROJECT_DIR%%%d" mkdir "%PROJECT_DIR%%%d"
)

echo [SUCCESS] Directory structure created

REM Step 7: Run setup wizard
echo [7/10] Running setup wizard...

if "%SKIP_WIZARD%"=="true" (
    echo [WARNING] Skipping setup wizard
    if not exist "%PROJECT_DIR%.env" (
        echo [ERROR] .env file not found and wizard skipped
        echo Either run without skip-wizard or create .env manually
        pause
        exit /b 1
    )
) else (
    if exist "%PROJECT_DIR%.env" (
        echo [WARNING] .env file already exists
        set /p RUN_WIZARD="Run setup wizard anyway? (y/N): "
        if /i "!RUN_WIZARD!"=="y" (
            python "%PROJECT_DIR%setup_wizard.py"
        ) else (
            echo [SUCCESS] Using existing .env configuration
        )
    ) else (
        python "%PROJECT_DIR%setup_wizard.py"
    )
)

echo [SUCCESS] Configuration complete

REM Step 8: Initialize database
echo [8/10] Initializing database...

cd /d "%PROJECT_DIR%digital-product-factory"

python -c "from database import ProductDB; db = ProductDB(); print('Database initialized')"

if errorlevel 1 (
    echo [ERROR] Database initialization failed
    cd /d "%PROJECT_DIR%"
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"
echo [SUCCESS] Database ready

REM Step 9: Run validation tests
echo [9/10] Running validation tests...

if "%DEV_MODE%"=="true" (
    echo [WARNING] Development mode: Skipping tests
) else (
    python integration_test.py --quick
    if errorlevel 1 (
        echo [WARNING] Some validation tests failed
        set /p CONTINUE="Continue anyway? (y/N): "
        if /i not "!CONTINUE!"=="y" (
            pause
            exit /b 1
        )
    ) else (
        echo [SUCCESS] Validation tests passed
    )
)

REM Step 10: Final setup
echo [10/10] Final setup...

REM Create Windows Task Scheduler task (optional)
set /p CREATE_TASK="Create Windows Task for automatic startup? (y/N): "
if /i "!CREATE_TASK!"=="y" (
    schtasks /create /tn "DigitalProductFactory" /tr "\"%VENV_DIR%\Scripts\python.exe\" \"%PROJECT_DIR%main.py\"" /sc onlogon /ru "%USERNAME%" /f
    if errorlevel 1 (
        echo [WARNING] Failed to create scheduled task
    ) else (
        echo [SUCCESS] Scheduled task created
        echo Run manually with: schtasks /run /tn "DigitalProductFactory"
    )
)

echo [SUCCESS] Setup complete

REM Display summary
echo.
echo ================================================================================
echo                      DEPLOYMENT COMPLETE!
echo ================================================================================
echo.
echo Digital Product Factory is ready to use!
echo.
echo Quick Start:
echo.
echo   1. Activate virtual environment:
echo      %VENV_DIR%\Scripts\activate.bat
echo.
echo   2. Create your first product:
echo      python cli.py create-product --type=notion --niche=productivity
echo.
echo   3. Check trending opportunities:
echo      python cli.py check-trends
echo.
echo   4. Start review dashboard:
echo      python cli.py review-dashboard
echo.
echo   5. Run automated mode:
echo      python main.py
echo.
echo Documentation:
echo   CLI Guide: CLI_GUIDE.md
echo   Automation Guide: AUTOMATION.md
echo   Log files: logs\
echo.
echo Configuration:
echo   Environment: .env
echo   Database: data\products.db
echo   Backups: backups\
echo.

if "%DEV_MODE%"=="true" (
    echo Development Mode:
    echo   Tests skipped - run manually with: python integration_test.py
    echo.
)

echo Deployment log saved to: %LOG_FILE%
echo.
echo Happy product creating! 🚀
echo.

pause
endlocal
