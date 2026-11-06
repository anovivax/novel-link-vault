@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 sync_windows.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python sync_windows.py
  goto :eof
)
echo ไม่พบ Python กรุณาติดตั้ง Python 3 ก่อนใช้งาน
pause
