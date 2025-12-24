# uninstall.ps1
# Vigilant Agent Uninstaller for Windows
# Run as Administrator

param(
    [string]$InstallPath = "C:\Vigilant",
    [switch]$Force
)

Write-Host "=== Vigilant Agent Uninstaller ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: Please run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Confirm uninstallation
if (-not $Force) {
    Write-Host "This will remove the Vigilant agent from this system." -ForegroundColor Yellow
    Write-Host "Installation path: $InstallPath" -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "Are you sure you want to uninstall? (yes/no)"
    
    if ($confirm -ne "yes") {
        Write-Host "Uninstallation cancelled" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "Uninstalling Vigilant Agent..."
Write-Host ""

$taskName = "VigilantAgent"

# Stop the scheduled task
Write-Host "Stopping scheduled task..."
try {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Write-Host "✓ Task stopped" -ForegroundColor Green
} catch {
    Write-Host "⚠ Task was not running" -ForegroundColor Yellow
}

# Remove the scheduled task
Write-Host "Removing scheduled task..."
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "✓ Task removed" -ForegroundColor Green
} catch {
    Write-Host "⚠ Task not found (may already be removed)" -ForegroundColor Yellow
}

# Check if installation directory exists
if (Test-Path $InstallPath) {
    Write-Host "Removing installation directory..."
    
    # Show what will be deleted
    $fileCount = (Get-ChildItem -Path $InstallPath -Recurse -File).Count
    Write-Host "  Found $fileCount files in $InstallPath"
    
    try {
        Remove-Item -Path $InstallPath -Recurse -Force -ErrorAction Stop
        Write-Host "✓ Installation directory removed" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to remove directory" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Write-Host ""
        Write-Host "You may need to manually delete: $InstallPath" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "⚠ Installation directory not found: $InstallPath" -ForegroundColor Yellow
}

# Success message
Write-Host ""
Write-Host "=== Uninstallation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Vigilant Agent has been removed from this system." -ForegroundColor Green
Write-Host ""

# Verify cleanup
Write-Host "Verification:" -ForegroundColor Cyan
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
$dirExists = Test-Path $InstallPath

if (-not $taskExists -and -not $dirExists) {
    Write-Host "✓ All components removed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ Some components may remain:" -ForegroundColor Yellow
    if ($taskExists) {
        Write-Host "  - Scheduled task still exists" -ForegroundColor Yellow
    }
    if ($dirExists) {
        Write-Host "  - Installation directory still exists" -ForegroundColor Yellow
    }
}

Write-Host ""