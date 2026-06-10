# Deploy the fixed Angel API to EC2 (Windows PowerShell)

$EC2_IP = "32.194.58.75"
$EC2_USER = "ubuntu"
$KEY_PATH = "$env:USERPROFILE\.ssh\stock-yard-key.pem"

function Run-SSH($command) {
    ssh -i $KEY_PATH "${EC2_USER}@${EC2_IP}" $command
}

function Copy-ToEC2($localFile, $remoteFile) {
    scp -i $KEY_PATH $localFile "${EC2_USER}@${EC2_IP}:${remoteFile}"
}

Write-Host "Deploying Angel API Fix to EC2" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if key file exists
if (-not (Test-Path $KEY_PATH)) {
    Write-Host "ERROR: SSH key not found at $KEY_PATH" -ForegroundColor Red
    exit 1
}

# Step 1: Copy new handler
Write-Host "1. Copying new handler to EC2..." -ForegroundColor Yellow
Copy-ToEC2 "angel_order_handler_http.py" "/home/ubuntu/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to copy handler file" -ForegroundColor Red
    exit 1
}

# Step 2: Copy service file
Write-Host "2. Copying updated service file..." -ForegroundColor Yellow
Copy-ToEC2 "angel-api.service" "/tmp/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to copy service file" -ForegroundColor Red
    exit 1
}

# Step 3: Update systemd service
Write-Host "3. Installing and restarting service..." -ForegroundColor Yellow

$ec2_commands = @'
    # Copy service file to systemd
    sudo cp /tmp/angel-api.service /etc/systemd/system/
    
    # Reload systemd daemon
    sudo systemctl daemon-reload
    
    # Stop old service if running
    sudo systemctl stop angel-api 2>/dev/null || true
    
    # Start new service
    sudo systemctl restart angel-api
    
    # Wait for startup
    sleep 2
    
    # Check status
    sudo systemctl status angel-api
    
    # Show logs
    echo ""
    echo "Service logs (last 15 lines):"
    sudo journalctl -u angel-api -n 15 --no-pager
'@

Run-SSH $ec2_commands

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "✓ Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Testing the service..." -ForegroundColor Cyan

# Test health endpoint
$maxRetries = 5
$retryCount = 0
$healthOk = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://${EC2_IP}:5000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            Write-Host "✓ Health Check: OK" -ForegroundColor Green
            Write-Host "  Status: $($data.status)" -ForegroundColor Green
            Write-Host "  Service: $($data.service)" -ForegroundColor Green
            $healthOk = $true
            break
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "  Attempt $retryCount/$maxRetries: Waiting for service to start..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

if ($healthOk) {
    Write-Host ""
    Write-Host "✓ Service is running and responding!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Test with: python trigger_telegram_trade.py" -ForegroundColor White
    Write-Host "2. Orders should now appear in Angel One account" -ForegroundColor White
    Write-Host "3. Check angel_orders.json for placement logs" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ Service health check failed" -ForegroundColor Red
    Write-Host "Run: ssh -i '$KEY_PATH' '${EC2_USER}@${EC2_IP}' 'sudo journalctl -u angel-api -n 20'" -ForegroundColor Yellow
    Write-Host "To see detailed error logs" -ForegroundColor Yellow
}
