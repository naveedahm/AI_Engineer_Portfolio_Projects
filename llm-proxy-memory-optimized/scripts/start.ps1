# start.ps1 - Lightweight start script
param(
    [switch]$NoMonitoring = $true  # Disable monitoring by default
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting LLM Gateway (Memory-Optimized)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check available memory
$os = Get-WmiObject Win32_OperatingSystem
$freeMemoryGB = [math]::Round($os.FreePhysicalMemory/1MB, 2)
Write-Host "Available Memory: ${freeMemoryGB}GB" -ForegroundColor Yellow

if ($freeMemoryGB -lt 4) {
    Write-Host "WARNING: Low memory! Close other applications." -ForegroundColor Red
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') { exit }
}

# Activate virtual environment
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

# Load environment variables
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}

# Start the server with limited resources
Write-Host "`nStarting API server..." -ForegroundColor Green
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Health: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop" -ForegroundColor Yellow

# Run with optimized settings
$env:PYTHONPATH = $PWD
python -c "
import uvicorn
import asyncio
from src.api.main import app

# Limit concurrency
uvicorn.run(
    app,
    host='0.0.0.0',
    port=8000,
    workers=1,
    limit_concurrency=30,
    limit_max_requests=1000,
    timeout_keep_alive=5
)
"