@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
set "ARENA_RESULT=%ERRORLEVEL%"
if not "%ARENA_RESULT%"=="0" pause
exit /b %ARENA_RESULT%
