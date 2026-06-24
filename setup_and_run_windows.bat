@echo off
setlocal
cd /d %~dp0

echo ======================================
echo  VISITOR PULSE UAS - Setup dan Run
echo ======================================

if not exist .venv (
    echo Membuat virtual environment...
    py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Server berjalan di: http://127.0.0.1:5000
echo Tekan CTRL + C untuk berhenti.
echo.
python app.py
pause
