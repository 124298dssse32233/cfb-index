@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0refresh_site.ps1"
