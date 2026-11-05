@echo off
chcp 65001 >nul
cd /d "%~dp0"
ZhigeFacultyEditor.exe --student --port 8005 --open
if errorlevel 1 pause
