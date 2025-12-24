# install.ps1
# Vigilant Agent Installer for Windows
# Run as Administrator

param(
    [Parameter(Mandatory=$true)]
    [string]$RigID,
    
    [Parameter(Mandatory=$true)]
    [string]$ServerURL,
    
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [string]$InstallPath = "C:\Vigilant"
)

Write-Host "=== Vigilant Agent Installer ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: Please run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check Python is installed
Write-Host "Checking prerequisites..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Found: $pythonVersion" -ForegroundColor Green

if ($pythonVersion -notmatch "Python 3\.[9-9]|Python 3\.1[0-9]") {
    Write-Host "WARNING: Python 3.9+ recommended. Found: $pythonVersion" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') { exit 1 }
}

# Create installation directory
Write-Host ""
Write-Host "Creating installation directory: $InstallPath"
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null

# Copy agent files
Write-Host "Copying agent files..."
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$currentDir\agent.py" "$InstallPath\" -Force
Copy-Item "$currentDir\logger.py" "$InstallPath\" -Force
Copy-Item "$currentDir\requirements.txt" "$InstallPath\" -Force

# Install Python dependencies
Write-Host "Installing Python dependencies..."
Set-Location $InstallPath
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create config file
Write-Host "Creating configuration file..."
$config = @{
    server_url = $ServerURL
    api_key = $ApiKey
    rig_id = $RigID
    metadata = @{
        location = "Lab A"
        capabilities = @("CAN", "Ethernet")
    }
    test_process_names = @("CANoe.exe", "TestRunner.exe")
} | ConvertTo-Json -Depth 10

$config | Out-File "$InstallPath\config.json" -Encoding UTF8
Write-Host "✓ Configuration created" -ForegroundColor Green

# Test connectivity (optional)
Write-Host ""
Write-Host "Testing server connectivity..."
try {
    $testUrl = "$ServerURL/health"
    $response = Invoke-WebRequest -Uri $testUrl -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Server reachable at $ServerURL" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Cannot reach server at $ServerURL" -ForegroundColor Yellow
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
    $continue = Read-Host "Continue installation anyway? (y/n)"
    if ($continue -ne 'y') { 
        Write-Host "Installation cancelled" -ForegroundColor Yellow
        exit 1 
    }
}

# Create Task Scheduler task
Write-Host ""
Write-Host "Creating scheduled task..."

$taskName = "VigilantAgent"
$pythonExe = (Get-Command python).Source
$scriptPath = "$InstallPath\agent.py"

# Create trigger (runs every 1 minute)
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# Create action
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPath `
    -WorkingDirectory $InstallPath

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register task
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Description "Vigilant Agent - Rig monitoring heartbeat" `
        -User "SYSTEM" `
        -RunLevel Highest `
        -Force | Out-Null
    
    Write-Host "✓ Scheduled task created" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Start the task
Write-Host "Starting agent..."
Start-ScheduledTask -TaskName $taskName

# Wait for first run
Start-Sleep -Seconds 5

# Verify installation
Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Installation Details:" -ForegroundColor Cyan
Write-Host "  Install Path:  $InstallPath"
Write-Host "  Rig ID:        $RigID"
Write-Host "  Server URL:    $ServerURL"
Write-Host "  Task Name:     $taskName"
Write-Host ""

# Check task status
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "Agent Status:" -ForegroundColor Cyan
Write-Host "  Last Run:      $($taskInfo.LastRunTime)"
Write-Host "  Last Result:   $($taskInfo.LastTaskResult) (0 = success)"
Write-Host "  Next Run:      $($taskInfo.NextRunTime)"

if ($taskInfo.LastTaskResult -eq 0) {
    Write-Host ""
    Write-Host "✓ Agent is running successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠ Agent may have issues. Check logs for details." -ForegroundColor Yellow
}

# Show useful commands
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:     Get-Content $InstallPath\logs\vigilant.log -Tail 20 -Wait"
Write-Host "  Check status:  Get-ScheduledTaskInfo -TaskName $taskName"
Write-Host "  Restart task:  Restart-ScheduledTask -TaskName $taskName"
Write-Host "  Stop task:     Stop-ScheduledTask -TaskName $taskName"
Write-Host "  Test manually: cd $InstallPath; python agent.py"
Write-Host "  Uninstall:     .\uninstall.ps1"
Write-Host ""
Write-Host "Log files are at: $InstallPath\logs\" -ForegroundColor Cyan
Write-Host ""