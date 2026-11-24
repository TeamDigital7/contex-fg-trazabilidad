@echo off
REM Lo usa la tarea programada: igual que iniciar.bat pero guarda lo que pasa en logs\app.log
cd /d "%~dp0.."
if not exist "logs" mkdir logs
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false >> "logs\app.log" 2>&1
