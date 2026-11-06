@echo off
chcp 65001 >nul
cd /d "%~dp0"
ZhigeFacultyEditor.exe --student --branch member-editor-test --port 8006 --open
if errorlevel 1 pause
