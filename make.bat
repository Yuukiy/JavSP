@echo off
REM Create exe from script

set activate=venv\Scripts\activate.bat
set deactivate=venv\Scripts\deactivate.bat

IF EXIST %activate% (
	@echo Activate vitualenv...
	call %activate%
)

python make\gen_ver_hook.py ver_hook.py
pyinstaller --clean --noconfirm make\windows.spec
del ver_hook.py
del dist\config.ini 2>nul
rmdir /s /q build
