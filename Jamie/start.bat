@echo off
title Jamie Discord Bot + Dashboard
cd /d "%~dp0"
echo ═══════════════════════════════════════
echo   JAMIE - Discord Bot + Dashboard
echo ═══════════════════════════════════════
echo.

REM Check for Python venv
if not exist "venv\Scripts\activate.bat" (
    echo [!] Python venv not found. Creating...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Check for Node modules
if not exist "dashboard\node_modules" (
    echo [!] Dashboard dependencies not found. Installing...
    cd dashboard
    npm install
    cd ..
)

echo [*] Starting Jamie Bot...
start "Jamie Bot" cmd /k "cd /d %~dp0 && venv\Scripts\python main.py"

echo [*] Starting Jamie Dashboard...
cd dashboard
start "Jamie Dashboard" cmd /k "cd /d %~dp0\dashboard && npm run dev"
cd ..

echo.
echo ═══════════════════════════════════════
echo   Jamie Bot:     Running in separate window
echo   Dashboard:     http://localhost:3000
echo ═══════════════════════════════════════
echo.
echo Press any key to close this launcher (bot and dashboard will keep running)...
pause >nul
