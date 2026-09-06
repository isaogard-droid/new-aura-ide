@echo off
rem Launcher for Windows. First run creates venv and installs deps.
setlocal
cd /d "%~dp0"
if not exist venv (
    echo [~] First run: creating venv and installing dependencies...
    py -3 -m venv venv
    venv\Scripts\python -m pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
    echo [v] Environment ready.
)
venv\Scripts\python transcribe.py %*
