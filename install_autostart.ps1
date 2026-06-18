# Register Firmware Validation Agent to start automatically at Windows logon.
# Run in PowerShell:  .\install_autostart.ps1

$ErrorActionPreference = "Stop"

$TaskName = "Firmware Validation Agent"
$ProjectDir = $PSScriptRoot
$StartScript = Join-Path $ProjectDir "start_agent.bat"

if (-not (Test-Path $StartScript)) {
    Write-Error "Missing start script: $StartScript"
}

$action = New-ScheduledTaskAction `
    -Execute $StartScript `
    -WorkingDirectory $ProjectDir

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Auto-start Firmware Validation Agent (Gmail monitor + weekly report)" `
    -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
Write-Host "  Trigger : At logon ($env:USERNAME)"
Write-Host "  Script  : $StartScript"
Write-Host ""
Write-Host "The agent will start automatically next time you log in to Windows."
Write-Host "To start now without rebooting, run:  .\start_agent.bat"
Write-Host "To remove autostart, run:              .\uninstall_autostart.ps1"
