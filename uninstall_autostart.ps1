# Remove Firmware Validation Agent from Windows startup.
# Run in PowerShell:  .\uninstall_autostart.ps1

$TaskName = "Firmware Validation Agent"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task not found: $TaskName (nothing to remove)"
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed scheduled task: $TaskName"
