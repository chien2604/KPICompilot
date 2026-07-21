# ============================================================
# KPICompilot - Ngrok Demo Launcher (Simple Version)
# ============================================================
# Cach dung:
#   1. Chay script nay trong PowerShell
#   2. Copy URL duoc hien thi va gui cho khach
#   3. Bam Ctrl+C khi demo xong
# ============================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   KPICompilot - Ngrok Demo Launcher     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Kiem tra cac service da chay chua
$frontendRunning = $false
$backendRunning = $false

try {
    $null = Invoke-WebRequest "http://localhost:5180" -TimeoutSec 2 -ErrorAction Stop
    $frontendRunning = $true
} catch { }

try {
    $null = Invoke-WebRequest "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    $backendRunning = $true
} catch { }

Write-Host "Trang thai services:" -ForegroundColor White
Write-Host "  Frontend (port 5180): $(if ($frontendRunning) { '✔ Dang chay' } else { '✘ CHUA CHAY - hay chay: npm run dev' })" -ForegroundColor $(if ($frontendRunning) { 'Green' } else { 'Red' })
Write-Host "  Backend  (port 8001): $(if ($backendRunning) { '✔ Dang chay' } else { '✘ CHUA CHAY - hay chay: python main.py' })" -ForegroundColor $(if ($backendRunning) { 'Green' } else { 'Red' })
Write-Host ""

if (-not $frontendRunning) {
    Write-Host "[CANH BAO] Frontend chua chay! Khach se khong xem duoc demo." -ForegroundColor Yellow
    Write-Host "  Chay trong terminal khac: cd N:\KPICompilot\frontend && npm run dev" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Dang khoi dong ngrok tunnel cho Frontend..." -ForegroundColor Green
Write-Host "(Vite proxy tu dong chuyen API requests den backend)" -ForegroundColor Gray
Write-Host ""

# Chay ngrok - Vite proxy se xu ly API calls den backend
# Them --host-header=rewrite neu gap loi CORS
Start-Process -FilePath "ngrok" -ArgumentList "http 5180 --log=stdout" -WindowStyle Normal

Start-Sleep -Seconds 3

# Lay URL tu ngrok API
$maxRetry = 5
$tunnelUrl = $null

for ($i = 0; $i -lt $maxRetry; $i++) {
    try {
        $response = Invoke-RestMethod "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $tunnel = $response.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1
        if ($tunnel) {
            $tunnelUrl = $tunnel.public_url
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($tunnelUrl) {
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  NGROK TUNNEL HOAT DONG!                                ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  LINK GUI CHO KHACH:" -ForegroundColor Yellow
    Write-Host "  $tunnelUrl" -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "  Ngrok Inspector: http://localhost:4040" -ForegroundColor Gray
    Write-Host ""
    
    # Copy vao clipboard
    $tunnelUrl | Set-Clipboard
    Write-Host "  [OK] Da copy vao clipboard!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Bam Ctrl+C hoac dong cua so ngrok khi demo xong." -ForegroundColor Gray
} else {
    Write-Host "[ERROR] Khong the lay URL tu ngrok." -ForegroundColor Red
    Write-Host "  Kiem tra tai: http://localhost:4040" -ForegroundColor Yellow
    Write-Host "  Hoac chay lenh: ngrok http 5180" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Nhan Enter de dong script nay (ngrok van chay trong cua so rieng)..."
Read-Host
