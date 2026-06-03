# test_chains.ps1 - Test different model families
Write-Host "Testing Different Model Chains" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Test 1: Default chain (fast, cheap)
Write-Host "`n[1] Testing DEFAULT chain (Fast & Cheap)..." -ForegroundColor Yellow
$body = @{
    messages = @(@{role = "user"; content = "What is 2+2? Answer briefly"})
    model_family = "default"
    max_tokens = 30
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat/completions" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host "Provider: $($response.provider)" -ForegroundColor Green
Write-Host "Model: $($response.model)" -ForegroundColor Green
Write-Host "Latency: $($response.latency_ms)ms" -ForegroundColor Green
Write-Host "Cost: `$$($response.cost)" -ForegroundColor Green
Write-Host "Response: $($response.response)" -ForegroundColor Gray

# Test 2: Premium chain (best quality)
Write-Host "`n[2] Testing PREMIUM chain (Best Quality)..." -ForegroundColor Yellow
$body = @{
    messages = @(@{role = "user"; content = "Explain quantum computing in one sentence"})
    model_family = "premium"
    max_tokens = 50
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat/completions" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host "Provider: $($response.provider)" -ForegroundColor Green
Write-Host "Model: $($response.model)" -ForegroundColor Green
Write-Host "Latency: $($response.latency_ms)ms" -ForegroundColor Green
Write-Host "Cost: `$$($response.cost)" -ForegroundColor Green
Write-Host "Response: $($response.response)" -ForegroundColor Gray

# Test 3: Balanced chain
Write-Host "`n[3] Testing BALANCED chain..." -ForegroundColor Yellow
$body = @{
    messages = @(@{role = "user"; content = "Write a haiku about coding"})
    model_family = "balanced"
    max_tokens = 50
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat/completions" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host "Provider: $($response.provider)" -ForegroundColor Green
Write-Host "Model: $($response.model)" -ForegroundColor Green
Write-Host "Latency: $($response.latency_ms)ms" -ForegroundColor Green
Write-Host "Cost: `$$($response.cost)" -ForegroundColor Green
Write-Host "Response: $($response.response)" -ForegroundColor Gray

# Test 4: Direct provider specification
Write-Host "`n[4] Direct to Groq Premium..." -ForegroundColor Yellow
$body = @{
    messages = @(@{role = "user"; content = "Say 'Premium model working'"})
    provider = "groq"
    model = "llama-3.3-70b-versatile"
    max_tokens = 20
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat/completions" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host "Provider: $($response.provider)" -ForegroundColor Green
Write-Host "Model: $($response.model)" -ForegroundColor Green