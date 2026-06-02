# scripts/setup_windows_with_monitoring.ps1
param(
    [switch]$SkipDocker = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LLM Gateway Setup with Monitoring" -ForegroundColor Cyan
Write-Host "Optimized for 16GB RAM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check available memory
$os = Get-WmiObject Win32_OperatingSystem
$freeMemoryGB = [math]::Round($os.FreePhysicalMemory/1MB, 2)
Write-Host "Available Memory: ${freeMemoryGB}GB" -ForegroundColor Yellow

if ($freeMemoryGB -lt 8) {
    Write-Host "WARNING: Low memory! Close other applications." -ForegroundColor Red
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') { exit }
}

# Step 1: Create virtual environment
Write-Host "`n[1/6] Creating Python virtual environment..." -ForegroundColor Green
python -m venv venv
& .\venv\Scripts\Activate.ps1

# Step 2: Install dependencies
Write-Host "`n[2/6] Installing Python dependencies..." -ForegroundColor Green
pip install --no-cache-dir fastapi uvicorn aiohttp pydantic python-dotenv pyyaml psutil

# Step 3: Create configuration
Write-Host "`n[3/6] Creating configuration..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "config\prometheus" | Out-Null
New-Item -ItemType Directory -Force -Path "config\grafana" | Out-Null

# Copy configuration files (create them if not exist)
if (-not (Test-Path "config\config.yaml")) {
    Copy-Item -Path "config.yaml.template" -Destination "config\config.yaml" -ErrorAction SilentlyContinue
}

# Step 4: Create .env file
Write-Host "`n[4/6] Creating .env file..." -ForegroundColor Green
if (-not (Test-Path ".env")) {
    @"
# Required API Keys
GROQ_API_KEY=your-groq-key-here
OPENAI_API_KEY=your-openai-key-here

# Optional
TOGETHER_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Budget
DAILY_BUDGET=5.0
HOURLY_BUDGET=1.0
"@ | Out-File -FilePath ".env" -Encoding utf8
    
    Write-Host "Please edit .env file and add your GROQ_API_KEY!" -ForegroundColor Yellow
}

# Step 5: Setup Docker monitoring (optional)
if (-not $SkipDocker) {
    Write-Host "`n[5/6] Setting up Docker monitoring stack..." -ForegroundColor Green
    
    # Check if Docker is running
    $dockerRunning = docker info 2>$null
    if (-not $dockerRunning) {
        Write-Host "Docker not running. Starting Docker Desktop..." -ForegroundColor Yellow
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        Start-Sleep -Seconds 15
    }
    
    # Pull images (lightweight)
    Write-Host "Pulling Prometheus (512MB)..." -ForegroundColor Yellow
    docker pull prom/prometheus:latest
    
    Write-Host "Pulling Grafana (256MB)..." -ForegroundColor Yellow
    docker pull grafana/grafana:latest
    
    Write-Host "Pulling Node Exporter (64MB)..." -ForegroundColor Yellow
    docker pull prom/node-exporter:latest
    
    Write-Host "Starting monitoring stack..." -ForegroundColor Green
    docker-compose up -d
}

# Step 6: Create start scripts
Write-Host "`n[6/6] Creating start scripts..." -ForegroundColor Green

# Create start script
@'
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
'@ | Out-File -FilePath "start_with_monitoring.ps1" -Encoding utf8

# Create stop script
@'
# stop_with_monitoring.ps1
Write-Host "Stopping LLM Gateway and monitoring..." -ForegroundColor Yellow

# Stop Docker services
docker-compose down

Write-Host "Services stopped." -ForegroundColor Green
'@ | Out-File -FilePath "stop_with_monitoring.ps1" -Encoding utf8

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file and add your GROQ_API_KEY" -ForegroundColor White
Write-Host "2. Run '.\start_with_monitoring.ps1' to start everything" -ForegroundColor White
Write-Host "3. Access Grafana at http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "4. Add Prometheus data source: http://prometheus:9090" -ForegroundColor White