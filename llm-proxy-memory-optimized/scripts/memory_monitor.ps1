# scripts/memory_monitor.ps1
Write-Host "Memory Monitor for LLM Gateway" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

function Get-MemoryUsage {
    $os = Get-WmiObject Win32_OperatingSystem
    $totalRAM = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
    $freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 2)
    $usedRAM = $totalRAM - $freeRAM
    $percentUsed = [math]::Round(($usedRAM / $totalRAM) * 100, 2)
    
    return @{
        Total = $totalRAM
        Used = $usedRAM
        Free = $freeRAM
        Percent = $percentUsed
    }
}

while ($true) {
    $memory = Get-MemoryUsage
    Write-Host "Memory Usage: $($memory.Used)GB / $($memory.Total)GB ($($memory.Percent)%)" -ForegroundColor Yellow
    
    if ($memory.Percent -gt 85) {
        Write-Host "WARNING: High memory usage! Consider:" -ForegroundColor Red
        Write-Host "  1. Close other applications" -ForegroundColor Red
        Write-Host "  2. Disable local models" -ForegroundColor Red
        Write-Host "  3. Restart the service" -ForegroundColor Red
    }
    
    Start-Sleep -Seconds 10
}