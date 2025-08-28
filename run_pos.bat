@echo off
cd /d "%~dp0"

echo ================================
echo  INSTALLING REQUIREMENTS...
echo ================================
python -m pip install -r requirements.txt

echo ================================
echo  STARTING POS APP...
echo ================================
python -m streamlit run app.py

pause
