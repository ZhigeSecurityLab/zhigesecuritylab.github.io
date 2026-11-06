@echo off
chcp 65001 >nul
cd /d "%~dp0"
ZhigeFacultyEditor.exe --student --branch faculty-editor-test --port 8005 --open
if errorlevel 1 pause
