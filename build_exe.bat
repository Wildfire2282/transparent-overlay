@echo off
rem Build a single-file exe into dist\TransparentOverlayV1.exe
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TransparentOverlayV1 TransparentOverlayV1.pyw
if errorlevel 1 (
    echo Build failed
    exit /b 1
)
echo Build complete: dist\TransparentOverlayV1.exe
