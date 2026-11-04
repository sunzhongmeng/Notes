@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Notes - Local Preview
if not exist ".venv\Scripts\python.exe" (
  echo Please create .venv and install dependencies as described in README.md.
  pause
  exit /b 1
)
echo Building Notes and opening the browser...
echo Keep this window open. Press Ctrl+C to stop the server.
echo Run this script again after editing your notes.
".venv\Scripts\python.exe" deploy\local\serve.py --auto-port
if errorlevel 1 pause
