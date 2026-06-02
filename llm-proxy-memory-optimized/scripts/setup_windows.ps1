# setup_windows.ps1 - Simplified setup for limited hardware
param(
    [switch]$WithLocalModels = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LLM Gateway Setup (Optimized for 16GB RAM)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Create virtual environment
Write-Host "`n[1/5] Creating Python virtual environment..." -ForegroundColor Green
python -m venv venv
.\venv\Scripts\Activate.ps1

# Step 2: Install minimal dependencies
Write-Host "`n[2/5] Installing dependencies (minimal)..." -ForegroundColor Green
pip install --no-cache-dir fastapi uvicorn aiohttp pydantic python-dotenv pyyaml

# Step 3: Create configuration
Write-Host "`n[3/5] Creating configuration..." -ForegroundColor Green
if (-not (Test-Path "config")) {
    New-Item -ItemType Directory -Path "config" -Force | Out-Null
}

# Create minimal config
@"
server:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  max_connections: 30

budget:
  daily_limit: 5.0
  hourly_limit: 1.0

models:
  lightweight:
    primary:
      provider: groq
      model: llama3-8b-8192
    fallbacks:
      - provider: openai
        model: gpt-3.5-turbo

providers:
  openai:
    api_key: `${OPENAI_API_KEY}
    timeout: 30
    enabled: true
  
  groq:
    api_key: `${GROQ_API_KEY}
    timeout: 20
    enabled: true
  
  together:
    api_key: `${TOGETHER_API_KEY}
    timeout: 30
    enabled: true
  
  ollama:
    enabled: $WithLocalModels
    base_url: http://localhost:11434
"@ | Out-File -FilePath "config\config.yaml" -Encoding utf8

# Step 4: Create .env file
Write-Host "`n[4/5] Creating .env file..." -ForegroundColor Green
if (-not (Test-Path ".env")) {
    @"
# Required API Keys (get from respective websites)
OPENAI_API_KEY=your-key-here
GROQ_API_KEY=your-key-here

# Optional API Keys
TOGETHER_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Budget limits (in USD)
DAILY_BUDGET=5.0
HOURLY_BUDGET=1.0
"@ | Out-File -FilePath ".env" -Encoding utf8
    
    Write-Host "Please edit .env file and add your API keys!" -ForegroundColor Yellow
}

# Step 5: Install Ollama (only if requested)
if ($WithLocalModels) {
    Write-Host "`n[5/5] Setting up Ollama for local models..." -ForegroundColor Green
    
    # Check if Ollama is installed
    $ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaInstalled) {
        Write-Host "Downloading Ollama..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile "$env:TEMP\OllamaSetup.exe"
        Start-Process -Wait -FilePath "$env:TEMP\OllamaSetup.exe" -ArgumentList "/S"
        Remove-Item "$env:TEMP\OllamaSetup.exe"
    }
    
    # Pull tiny model only
    Write-Host "Pulling tiny model (1.5GB) - this will take a few minutes..." -ForegroundColor Yellow
    ollama pull llama3.2:1b  # Very small model, only 1.5GB
    
    # Start Ollama service
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
}
else {
    Write-Host "`n[5/5] Skipping local models setup (use -WithLocalModels to enable)" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file and add your API keys" -ForegroundColor White
Write-Host "2. Run '.\start.ps1' to start the gateway" -ForegroundColor White
Write-Host "3. Test with: curl http://localhost:8000/health" -ForegroundColor White