@echo off
chcp 65001 >nul
cd /d "%~dp0"
ZhigeFacultyEditor.exe --user zhengfeiLian --branch faculty-editor-test --port 8003 --open
if errorlevel 1 pause
