@echo off
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%cli.py" %*
) else (
  py "%SCRIPT_DIR%cli.py" %*
)
