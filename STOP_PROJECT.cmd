@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-project.ps1" %*
if errorlevel 1 (
  echo.
  echo Stop failed. Read the message above, then press any key to close.
  pause >nul
  exit /b 1
)
