@echo off
REM Ejecutar como administrador. Detiene la app y quita el arranque automatico y la regla del firewall.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Stop-ScheduledTask -TaskName 'Contex Trazabilidad' -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'Contex Trazabilidad' -Confirm:$false -ErrorAction SilentlyContinue; Remove-NetFirewallRule -DisplayName 'Contex Trazabilidad' -ErrorAction SilentlyContinue; Write-Host 'Arranque automatico quitado.'"
pause
