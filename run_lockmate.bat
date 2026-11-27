@echo off
REM LOCKMATE — Start Backend and Frontend
REM Run this from the lockmate repository root

set PROJECT_ROOT=%~dp0
cd /d %PROJECT_ROOT%

echo ==========================================
echo LOCKMATE - Healthcare Privacy Dashboard
echo ==========================================
echo.

REM Check for RAKSHA_SECRET
if "%RAKSHA_SECRET%"=="" (
    echo WARNING: RAKSHA_SECRET environment variable not set!
    echo Using default practice secret for demo...
    set RAKSHA_SECRET=cHJhY3RpY2U=  REM base64 for "practice"
    echo RAKSHA_SECRET=%RAKSHA_SECRET%
    echo.
)

REM Create frontend_runs directory
if not exist frontend_runs mkdir frontend_runs

echo Starting LOCKMATE Backend API on http://127.0.0.1:8000
echo Starting LOCKMATE Frontend on http://127.0.0.1:5173
echo.
echo Press Ctrl+C in each window to stop.
echo.

REM Start backend in new window
start "LOCKMATE Backend" cmd /k "
    cd /d %PROJECT_ROOT%
    set RAKSHA_SECRET=%RAKSHA_SECRET%
    python -m uvicorn secret_wards.api.server:app --host 127.0.0.1 --port 8000 --reload
"

REM Wait a moment for backend to start
timeout /t 3 >nul

REM Start frontend in new window
start "LOCKMATE Frontend" cmd /k "
    cd /d %PROJECT_ROOT%\lockmate-frontend
    npm run dev
"

echo Both services starting...
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo.
echo API Health: http://127.0.0.1:8000/api/health
echo.