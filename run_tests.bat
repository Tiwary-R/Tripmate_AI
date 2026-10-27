@echo off
cd /d "%~dp0"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python evaluate_suite.py
