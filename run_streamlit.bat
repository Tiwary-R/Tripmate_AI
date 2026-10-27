@echo off
REM TripMate AI - Streamlit launcher (Windows)
cd /d "%~dp0"
if not exist .venv (
    echo Creating virtual environment and installing packages...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist .env copy .env.example .env
echo Starting TripMate AI (Streamlit)...
.venv\Scripts\python -m streamlit run streamlit_app.py
