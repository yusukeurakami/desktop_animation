@echo off
setlocal
cd /d "%~dp0"

set "SCRIPT=%~dp0LibertyPet.ps1"

if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
  "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
)

if errorlevel 1 (
  echo.
  echo Liberty Desktop Pet failed to start.
  echo If you see an error above, please copy it and share it.
  echo.
  pause
)
