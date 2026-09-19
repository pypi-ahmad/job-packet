@echo off
setlocal
cd /d "%~dp0"

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
    ) else (
        type nul > .env
    )
    notepad .env
    exit /b 0
)

if not exist .venv (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
