@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Jarvis isn't set up yet. Running setup...
  powershell -ExecutionPolicy Bypass -File setup.ps1 || exit /b 1
)
".venv\Scripts\python.exe" -m jarvis %*
if errorlevel 1 pause
