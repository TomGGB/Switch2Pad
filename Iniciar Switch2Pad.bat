@echo off
rem Ejecuta Switch2Pad desde el codigo fuente (la version compilada es dist\Switch2Pad.exe)
cd /d "%~dp0"
start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" -m switch2pad
