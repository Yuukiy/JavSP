@echo off
REM Create exe from script

pyinstaller --clean --noconfirm make\windows.spec
del dist\config.ini 2>nul
rmdir /s /q build
