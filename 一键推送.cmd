@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Notes - Push to GitHub
if not exist ".venv\Scripts\python.exe" (
  echo Please set up .venv as described in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "deploy\github-pages\push.py"
set "push_result=%errorlevel%"
echo.
pause
exit /b %push_result%
