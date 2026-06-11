@echo off
title CFB Index - Build Status Launcher
echo.
echo   Starting your build-status dashboard...
echo.
start "CFB Build Status (close this window to stop)" /min "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\status_server.py"
timeout /t 2 >nul
start "" http://localhost:8787/
echo   Opened  http://localhost:8787  in your browser.
echo.
echo   A small MINIMIZED window titled "CFB Build Status" is now
echo   running the dashboard. Close THAT window when you're done.
echo   (You can close this window now.)
echo.
timeout /t 6 >nul
