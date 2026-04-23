@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0publish_site.ps1"
