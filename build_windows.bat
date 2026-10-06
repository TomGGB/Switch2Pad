@echo off
rem Compila dist\Switch2Pad.exe (requiere Python 3.10+)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean switch2pad.spec || exit /b 1
echo.
echo Listo: dist\Switch2Pad.exe
