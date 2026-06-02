# start_with_monitoring.ps1
Write-Host "Starting LLM Gateway with Monitoring..." -ForegroundColor Cyan

# Start Docker monitoring if not running
$monitoringRunning = docker ps --filter "name=prometheus" --format "table {{.Names}}" | Select-String "prometheus"
if (-not $monitoringRunning) {
    Write-Host "Starting monitoring stack..." -ForegroundColor Yellow
    docker-compose up -d
    Start-Sleep -Seconds 5
}

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}

# Start the API
Write-Host "Starting API server..." -ForegroundColor Green
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Metrics: http://localhost:8000/metrics" -ForegroundColor Cyan
Write-Host "Prometheus: http://localhost:9090" -ForegroundColor Cyan
Write-Host "Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

python -c "import uvicorn; from src.api.main import app; uvicorn.run(app, host='0.0.0.0', port=8000, workers=1)"
