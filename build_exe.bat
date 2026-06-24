@echo off
setlocal
cd /d %~dp0

py -m PyInstaller --noconfirm --clean --onefile --name LIFTClassroomUploader --add-data "templates;templates" --exclude-module torch --exclude-module torchvision --exclude-module torchaudio --exclude-module scipy --exclude-module sklearn --exclude-module matplotlib main.py

echo.
echo Build complete.
echo Your executable is in the dist folder.
