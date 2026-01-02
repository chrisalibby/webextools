# PowerShell script to create a Windows Task Scheduler task for Webex CDR Downloader
# This will run the CDR downloader every 15 minutes, regardless of user login status

# Configuration
$TaskName = "Webex CDR Downloader"
$TaskDescription = "Automatically downloads Webex Call Detail Records to SQL Server every 15 minutes"
$ScriptPath = "$PSScriptRoot\webex_cdr_downloader.py"
$PythonPath = (Get-Command python).Source
$WorkingDirectory = $PSScriptRoot
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Verify paths exist
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found at: $ScriptPath"
    exit 1
}

if (-not $PythonPath) {
    Write-Error "Python not found in PATH. Please install Python first."
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Webex CDR Downloader - Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Task Name:          $TaskName"
Write-Host "  Python Path:        $PythonPath"
Write-Host "  Script Path:        $ScriptPath"
Write-Host "  Working Directory:  $WorkingDirectory"
Write-Host "  Run As User:        $CurrentUser"
Write-Host "  Frequency:          Every 15 minutes"
Write-Host "  Run When:           User logged off (using stored credentials)"
Write-Host ""

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "Task '$TaskName' already exists." -ForegroundColor Yellow
    $Overwrite = Read-Host "Do you want to replace it? (Y/N)"

    if ($Overwrite -ne "Y" -and $Overwrite -ne "y") {
        Write-Host "Setup cancelled." -ForegroundColor Red
        exit 0
    }

    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the scheduled task action
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $WorkingDirectory

# Create the trigger (every 15 minutes, indefinitely)
# Note: For indefinite repetition, we don't specify RepetitionDuration
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)

# Create the principal (run whether user is logged on or not)
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType S4U `
    -RunLevel Highest

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register the scheduled task
try {
    Write-Host ""
    Write-Host "Creating scheduled task..." -ForegroundColor Yellow

    $Task = Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Force

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "SUCCESS! Task Scheduler setup complete!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Yellow
    Write-Host "  Name:               $TaskName"
    Write-Host "  Status:             $($Task.State)"
    Write-Host "  Next Run Time:      $($Task.NextRunTime)"
    Write-Host "  Schedule:           Every 15 minutes, indefinitely"
    Write-Host "  Run when logged off: YES (using your credentials)"
    Write-Host ""
    Write-Host "Management:" -ForegroundColor Yellow
    Write-Host "  View in Task Scheduler:"
    Write-Host "    1. Press Win+R and type: taskschd.msc"
    Write-Host "    2. Look for '$TaskName' in Task Scheduler Library"
    Write-Host ""
    Write-Host "  Test the task immediately:"
    Write-Host "    Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "  View task history:"
    Write-Host "    Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
    Write-Host ""
    Write-Host "  Disable the task:"
    Write-Host "    Disable-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "  Enable the task:"
    Write-Host "    Enable-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "  Remove the task:"
    Write-Host "    Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    Write-Host ""
    Write-Host "IMPORTANT NOTES:" -ForegroundColor Cyan
    Write-Host "  - The task will run using your current Windows credentials"
    Write-Host "  - Webex and SQL Server credentials are stored securely in Windows Credential Manager"
    Write-Host "  - The task will run even when you're logged off"
    Write-Host "  - Check sync statistics with: python webex_cdr_downloader.py --stats"
    Write-Host ""

    # Ask if user wants to test the task now
    Write-Host "Would you like to run the task once now to test it? (Y/N): " -ForegroundColor Yellow -NoNewline
    $RunNow = Read-Host

    if ($RunNow -eq "Y" -or $RunNow -eq "y") {
        Write-Host ""
        Write-Host "Starting task..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task started! Check the console output or run 'python webex_cdr_downloader.py --stats' to see results." -ForegroundColor Green
    }

    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. Not running PowerShell as Administrator"
    Write-Host "     Solution: Right-click PowerShell and select 'Run as Administrator'"
    Write-Host ""
    Write-Host "  2. Execution policy prevents script execution"
    Write-Host "     Solution: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    Write-Host ""
    exit 1
}
