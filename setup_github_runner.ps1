# GitHub Self-Hosted Runner Setup Script
# Run this in PowerShell as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Self-Hosted Runner Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Step 1: Check your public IP
Write-Host "Step 1: Checking your public IP..." -ForegroundColor Cyan
try {
    $publicIP = (Invoke-WebRequest -Uri "https://ifconfig.me" -UseBasicParsing).Content.Trim()
    Write-Host "✅ Your public IP: $publicIP" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Whitelist this IP with Angel One!" -ForegroundColor Yellow
    Write-Host "   Contact Angel One support and ask them to whitelist: $publicIP" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "⚠️  Could not detect public IP. Check manually at: https://ifconfig.me" -ForegroundColor Yellow
    Write-Host ""
}

# Step 2: Create runner directory
Write-Host "Step 2: Creating runner directory..." -ForegroundColor Cyan
$runnerPath = "C:\actions-runner"
if (Test-Path $runnerPath) {
    Write-Host "⚠️  Directory already exists: $runnerPath" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to overwrite? (y/n)"
    if ($overwrite -ne 'y') {
        Write-Host "❌ Setup cancelled" -ForegroundColor Red
        exit 1
    }
    Remove-Item -Path $runnerPath -Recurse -Force
}

New-Item -ItemType Directory -Path $runnerPath | Out-Null
Write-Host "✅ Created directory: $runnerPath" -ForegroundColor Green
Write-Host ""

# Step 3: Download runner
Write-Host "Step 3: Downloading GitHub Runner..." -ForegroundColor Cyan
$runnerVersion = "2.311.0"
$runnerUrl = "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
$zipPath = "$runnerPath\actions-runner.zip"

try {
    Invoke-WebRequest -Uri $runnerUrl -OutFile $zipPath
    Write-Host "✅ Downloaded runner v$runnerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to download runner: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Extract runner
Write-Host "Step 4: Extracting runner..." -ForegroundColor Cyan
try {
    Expand-Archive -Path $zipPath -DestinationPath $runnerPath -Force
    Remove-Item -Path $zipPath
    Write-Host "✅ Extracted runner files" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to extract: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Get GitHub token
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 5: Configure Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To get your GitHub token:" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/YOUR_USERNAME/Stock-Yard/settings/actions/runners/new" -ForegroundColor Yellow
Write-Host "2. Select 'Windows' as the operating system" -ForegroundColor Yellow
Write-Host "3. Copy the token from the 'Configure' section" -ForegroundColor Yellow
Write-Host ""

$repoUrl = Read-Host "Enter your repository URL (e.g., https://github.com/username/Stock-Yard)"
$token = Read-Host "Enter the runner token from GitHub"

Write-Host ""
Write-Host "Configuring runner..." -ForegroundColor Cyan

# Step 6: Configure runner
Set-Location $runnerPath
try {
    $configArgs = @(
        "--url", $repoUrl,
        "--token", $token,
        "--name", "angel-one-runner",
        "--labels", "self-hosted,Windows,X64",
        "--work", "_work",
        "--unattended"
    )
    
    & ".\config.cmd" $configArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Runner configured successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Runner configuration failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Configuration error: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 7: Install as service
Write-Host "Step 7: Installing runner as Windows service..." -ForegroundColor Cyan
try {
    & ".\svc.sh" install
    Write-Host "✅ Service installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Service installation failed: $_" -ForegroundColor Red
    Write-Host "   You can run the runner manually with: .\run.cmd" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Start service
Write-Host "Step 8: Starting runner service..." -ForegroundColor Cyan
try {
    & ".\svc.sh" start
    Write-Host "✅ Service started" -ForegroundColor Green
} catch {
    Write-Host "❌ Service start failed: $_" -ForegroundColor Red
    Write-Host "   You can run the runner manually with: .\run.cmd" -ForegroundColor Yellow
}
Write-Host ""

# Step 9: Verify installation
Write-Host "Step 9: Verifying installation..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $status = & ".\svc.sh" status
    Write-Host "✅ Runner status: $status" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not verify status" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. ✅ Whitelist your IP ($publicIP) with Angel One" -ForegroundColor White
Write-Host "2. ✅ Verify runner is online at:" -ForegroundColor White
Write-Host "   https://github.com/YOUR_USERNAME/Stock-Yard/settings/actions/runners" -ForegroundColor White
Write-Host "3. ✅ Test by triggering an Angel One order" -ForegroundColor White
Write-Host ""
Write-Host "Runner Commands:" -ForegroundColor Yellow
Write-Host "  Check status:  cd $runnerPath; .\svc.sh status" -ForegroundColor White
Write-Host "  Stop service:  cd $runnerPath; .\svc.sh stop" -ForegroundColor White
Write-Host "  Start service: cd $runnerPath; .\svc.sh start" -ForegroundColor White
Write-Host "  View logs:     cd $runnerPath; Get-Content _diag\Runner_*.log -Tail 50" -ForegroundColor White
Write-Host ""
Write-Host "The runner will auto-start with Windows!" -ForegroundColor Green
Write-Host ""
