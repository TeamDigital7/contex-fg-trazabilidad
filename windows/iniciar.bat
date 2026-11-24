@echo off
REM Arranca la app. Queda disponible en http://NOMBRE-DEL-SERVIDOR:8501 para toda la red de Contex.
cd /d "%~dp0.."
if not exist "logs" mkdir logs
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
