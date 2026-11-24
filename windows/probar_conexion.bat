@echo off
REM Prueba la conexion al SQL Server con lo configurado en .streamlit\secrets.toml (solo lectura).
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\probar_conexion.py
pause
