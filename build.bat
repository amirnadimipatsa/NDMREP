@echo off
echo Installing required Python packages...
pip install -r requirements.txt

echo.
echo Building EXE file...
pyinstaller --noconsole --onefile component_tester_app.py

echo.
echo Build completed!
pause
