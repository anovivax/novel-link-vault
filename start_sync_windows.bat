@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 sync_windows.py
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python sync_windows.py
  goto end
)
echo Python not found. Please install Python 3.9 or later.
:end
pause
