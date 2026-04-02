@echo off
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%cli.py" %*
  goto :eof
)
where py >nul 2>&1
if not errorlevel 1 (
  py "%SCRIPT_DIR%cli.py" %*
  goto :eof
)
python "%SCRIPT_DIR%cli.py" %*
