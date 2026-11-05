@echo off
chcp 65001 >nul
cd /d "%~dp0"
ZhigeFacultyEditor.exe --user garrisongys --branch main --port 8002 --open
if errorlevel 1 pause
