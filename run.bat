@echo off
echo ============================================
echo   AI Video Studio - starting...
echo   A browser page will open automatically.
echo ============================================
pip install -r requirements.txt
streamlit run app.py
pause
