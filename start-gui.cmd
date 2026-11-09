@echo off
setlocal
cd /d "%~dp0"
if exist "SDTrimSP-2D_GUI.exe" (
  start "" "%~dp0SDTrimSP-2D_GUI.exe"
  exit /b 0
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0bootstrap.py" %*
) else (
  python "%~dp0bootstrap.py" %*
)
if errorlevel 1 (
  echo.
  echo Could not start. Install Python 3.11+ from https://www.python.org/downloads/windows/
  echo Or download the Windows installer/portable package; those need no Python.
  pause
)
