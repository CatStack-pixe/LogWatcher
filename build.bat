@echo off
echo Cleaning previous builds...
rmdir /s /q build dist

echo Installing dependencies...
pip install -r requirements.txt

echo Checking tkdnd...
python -c "from tkinterdnd2 import TkinterDnD;print('tkdnd available')" || echo tkdnd not found

echo Building executable...
pyinstaller build_config.spec --clean --noconfirm

echo Done!
pause