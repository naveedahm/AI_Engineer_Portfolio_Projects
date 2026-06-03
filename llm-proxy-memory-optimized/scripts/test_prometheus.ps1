# test_prometheus.ps1
Write-Host "Testing Prometheus LLM Metrics" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

# Test 1: Check if Prometheus is accessible
Write-Host "`n[1] Checking Prometheus..." -ForegroundColor Yellow
try {
    $prometheus = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/query?query=up" -ErrorAction Stop
    Write-Host "✅ Prometheus is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Prometheus not accessible - Start it first" -ForegroundColor Red
    exit
}

# Test 2: Check target status
Write-Host "`n[2] Checking LLM Gateway target..." -ForegroundColor Yellow
$targets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets"
$target = $targets.data.activeTargets | Where-Object { $_.labels.job -eq "llm-gateway" }
if ($target.health -eq "up") {
    Write-Host "✅ Target is UP" -ForegroundColor Green
} else {
    Write-Host "❌ Target is DOWN - Error: $($target.lastError)" -ForegroundColor Red
}

# Test 3: Query LLM metrics
Write-Host "`n[3] Querying LLM metrics..." -ForegroundColor Yellow
$queries = @(
    "sum(llm_requests_total)",
    "sum(llm_cost_dollars_total)",
    "count({__name__=~'llm_.+'})"
)

foreach ($query in $queries) {
    $result = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/query?query=$query"
    $value = $result.data.result[0].value[1]
    Write-Host "  $query = $value" -ForegroundColor Gray
}

# Test 4: List all LLM metrics
Write-Host "`n[4] Available LLM metrics:" -ForegroundColor Yellow
$metrics = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/label/__name__/values"
$llmMetrics = $metrics.data | Where-Object { $_ -like "llm_*" }
foreach ($metric in $llmMetrics) {
    Write-Host "  - $metric" -ForegroundColor Green
}

Write-Host "`n✅ Testing complete!" -ForegroundColor Green
Write-Host "Access Prometheus UI: http://localhost:9090" -ForegroundColor Cyan