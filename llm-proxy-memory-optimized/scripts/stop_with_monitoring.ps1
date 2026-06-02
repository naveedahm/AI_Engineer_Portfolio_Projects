# stop_with_monitoring.ps1
Write-Host "Stopping LLM Gateway and monitoring..." -ForegroundColor Yellow

# Stop Docker services
docker-compose down

Write-Host "Services stopped." -ForegroundColor Green
