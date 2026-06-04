# hf_diagnostic.ps1
Write-Host "Hugging Face DNS Diagnostic" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

# 1. Test DNS with different servers
Write-Host "`n[1] Testing DNS resolution..." -ForegroundColor Yellow
$servers = @("8.8.8.8", "1.1.1.1", "208.67.222.222")
foreach ($dns in $servers) {
    try {
        $result = nslookup api-inference.huggingface.co $dns 2>$null
        if ($result -match "Address: \d+\.\d+\.\d+\.\d+") {
            Write-Host "✅ DNS works with $dns" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ DNS failed with $dns" -ForegroundColor Red
    }
}

# 2. Check if Hugging Face is blocked
Write-Host "`n[2] Testing connectivity..." -ForegroundColor Yellow
try {
    $response = curl -UseBasicParsing -TimeoutSec 10 "https://huggingface.co" 2>$null
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ huggingface.co is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ huggingface.co blocked/unreachable" -ForegroundColor Red
}

# 3. Check hosts file
Write-Host "`n[3] Checking hosts file..." -ForegroundColor Yellow
$hostsFile = Get-Content "$env:windir\System32\drivers\etc\hosts"
if ($hostsFile -match "api-inference.huggingface.co") {
    Write-Host "⚠️  Found entry in hosts file" -ForegroundColor Yellow
    $hostsFile | Select-String "api-inference"
} else {
    Write-Host "✅ No conflicting hosts entry" -ForegroundColor Green
}