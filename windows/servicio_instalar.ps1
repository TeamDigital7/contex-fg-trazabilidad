# Contex FYG - Trazabilidad: arranque automatico al encender el servidor (tarea programada de Windows).
# Se usa una tarea programada y no un "servicio" porque no necesita instalar programas extra.
$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERROR] Ejecuta este archivo como administrador (clic derecho > Ejecutar como administrador)."
    exit 1
}
$bat = Join-Path $PSScriptRoot "iniciar_en_segundo_plano.bat"
$nombre = "Contex Trazabilidad"
$accion = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`""
$inicio = New-ScheduledTaskTrigger -AtStartup
# Sin limite de tiempo (por defecto Windows corta las tareas a las 72 h) y se reinicia sola si se cae.
$ajustes = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
           -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $inicio -Settings $ajustes `
    -User "SYSTEM" -RunLevel Highest -Force | Out-Null
# Puerto 8501 solo para la red interna (perfiles Dominio y Privado, nunca Publico)
if (-not (Get-NetFirewallRule -DisplayName $nombre -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $nombre -Direction Inbound -Protocol TCP -LocalPort 8501 `
        -Action Allow -Profile Domain,Private | Out-Null
}
Start-ScheduledTask -TaskName $nombre
Write-Host ""
Write-Host "Listo. La app arranca sola con el servidor."
Write-Host "Abrela desde cualquier PC de la red en:  http://$($env:COMPUTERNAME):8501"
Write-Host "Si algo falla, revisa el archivo logs\app.log"
