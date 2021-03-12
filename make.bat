@echo off
REM Create exe from script

pyinstaller --clean --noconfirm make\windows.spec
rmdir /s /q build
