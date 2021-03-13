@echo off
REM Create exe from script

set activate=venv\Scripts\activate.bat
set deactivate=venv\Scripts\deactivate.bat

IF EXIST %activate% (
	@echo Activate vitualenv...
	call %activate%
)

pyinstaller --clean --noconfirm make\windows.spec
del dist\config.ini 2>nul
rmdir /s /q build
