@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PORT=8595"

if not exist .env (
    copy .env.example .env >nul
    notepad .env
    exit /b 0
)

if not exist .venv (
    py -3 -m venv .venv
)

set "FOUND_PORT=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "FOUND_PORT=1"
    echo Stopping existing process on port %PORT% ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)

if "%FOUND_PORT%"=="1" (
    timeout /t 1 /nobreak >nul
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
        echo Could not release port %PORT% ^(PID %%P^).
        exit /b 1
    )
)

.venv\Scripts\pip install -r requirements.txt

echo Starting Job Packet Generator at http://localhost:%PORT%
.venv\Scripts\streamlit run app.py --server.port %PORT%
