# Self-Hosted GitHub Runner Setup for Angel One

Run GitHub Actions on YOUR computer instead of GitHub's servers. This uses your home IP which Angel One allows.

---

## Overview

**How it works:**
```
GitHub → Your PC (Self-Hosted Runner) → Angel One API ✅
```

Instead of running on GitHub's servers (dynamic IP), the workflow runs on your PC (your home IP).

---

## Prerequisites

1. ✅ Windows PC that can stay on during trading hours
2. ✅ Stable internet connection
3. ✅ GitHub repository access
4. ✅ Angel One credentials

**Optional but recommended:**
- Static IP from your ISP (contact them - may be free or ₹100-500/month)
- If you have dynamic IP, whitelist it with Angel One whenever it changes

---

## Step 1: Check Your Current IP

```powershell
# Check your public IP
curl ifconfig.me
```

**Note this IP** - you'll need to whitelist it with Angel One.

---

## Step 2: Whitelist Your IP with Angel One

1. Contact Angel One support
2. Ask them to whitelist your home IP for API access
3. Provide them the IP from Step 1
4. Wait for confirmation (usually 1-2 business days)

---

## Step 3: Install GitHub Self-Hosted Runner

### 3.1 Go to Your GitHub Repository

1. Open your repo: https://github.com/YOUR_USERNAME/Stock-Yard
2. Go to **Settings** → **Actions** → **Runners**
3. Click **"New self-hosted runner"**
4. Select **Windows**

### 3.2 Download and Configure Runner

GitHub will show you commands. Run them in PowerShell (as Administrator):

```powershell
# Create a folder for the runner
mkdir actions-runner
cd actions-runner

# Download the runner (GitHub provides the exact command)
# Example:
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-win-x64-2.311.0.zip -OutFile actions-runner-win-x64-2.311.0.zip

# Extract
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD/actions-runner-win-x64-2.311.0.zip", "$PWD")

# Configure the runner
./config.cmd --url https://github.com/YOUR_USERNAME/Stock-Yard --token YOUR_TOKEN

# When prompted:
# - Runner name: angel-one-runner (or any name)
# - Runner group: Default
# - Labels: self-hosted,Windows,X64
# - Work folder: _work (default)
```

### 3.3 Install as Windows Service (Auto-start)

```powershell
# Install as service (runs automatically on startup)
./svc.sh install

# Start the service
./svc.sh start

# Check status
./svc.sh status
```

**Alternative: Run manually (for testing)**
```powershell
# Run in foreground (for testing)
./run.cmd
```

---

## Step 4: Update GitHub Actions Workflow

Update `.github/workflows/angel_trade.yml` to use your self-hosted runner:

```yaml
name: Angel One Trade Executor

on:
  repository_dispatch:
    types: [place_trade]

permissions:
  contents: write

jobs:
  execute-trade:
    runs-on: self-hosted  # ← Changed from ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install smartapi-python pyotp requests logzero websocket-client

    - name: Log trade request
      run: |
        echo "📊 Angel One Order Request"
        echo "Stock       : ${{ github.event.client_payload.symbol }}"
        echo "Action      : ${{ github.event.client_payload.action }}"
        echo "Entry Price : ₹${{ github.event.client_payload.price }}"
        echo "Quantity    : ${{ github.event.client_payload.quantity }}"

    - name: Execute trade on Angel One
      env:
        ANGEL_API_KEY:      ${{ secrets.ANGEL_API_KEY }}
        ANGEL_CLIENT_ID:    ${{ secrets.ANGEL_CLIENT_ID }}
        ANGEL_PASSWORD:     ${{ secrets.ANGEL_PASSWORD }}
        ANGEL_TOTP_SECRET:  ${{ secrets.ANGEL_TOTP_SECRET }}
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
        TRADE_SYMBOL:       ${{ github.event.client_payload.symbol }}
        TRADE_ACTION:       ${{ github.event.client_payload.action }}
        TRADE_PRICE:        ${{ github.event.client_payload.price }}
        TRADE_QUANTITY:     ${{ github.event.client_payload.quantity }}
      run: |
        echo "🚀 Executing trade..."
        python angel_trade.py
        echo "✅ Trade execution completed"

    - name: Commit order log
      run: |
        git config --global user.name "GitHub Action"
        git config --global user.email "action@github.com"
        git add radar_trades.json || echo "No radar file"
        git commit -m "📊 Order log: ${{ github.event.client_payload.action }} ${{ github.event.client_payload.symbol }}" || echo "No changes"
        git push || echo "Push failed"
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Step 5: Test the Setup

### 5.1 Trigger a Test Order

From your repository, trigger a test order:

```bash
# Using GitHub CLI (install from: https://cli.github.com/)
gh api repos/YOUR_USERNAME/Stock-Yard/dispatches \
  -f event_type=place_trade \
  -f client_payload[symbol]=SBIN \
  -f client_payload[action]=BUY \
  -f client_payload[price]=850.50 \
  -f client_payload[quantity]=1
```

### 5.2 Check Runner Logs

On your PC, check the runner logs:

```powershell
cd actions-runner
# Logs are in _diag folder
Get-Content _diag\Runner_*.log -Tail 50
```

Or check on GitHub:
- Go to your repo → **Actions** tab
- Click on the latest workflow run
- Check the logs

---

## Step 6: Keep Runner Running 24/7

### Option A: Windows Service (Recommended)

Already done in Step 3.3 - the runner auto-starts with Windows.

### Option B: Task Scheduler (Alternative)

1. Open **Task Scheduler**
2. Create Basic Task:
   - Name: `GitHub Runner`
   - Trigger: **At startup**
   - Action: **Start a program**
   - Program: `C:\actions-runner\run.cmd`
   - Start in: `C:\actions-runner`

---

## Maintenance

### Check Runner Status

```powershell
cd actions-runner
./svc.sh status
```

### Restart Runner

```powershell
./svc.sh stop
./svc.sh start
```

### Update Runner

```powershell
# Stop service
./svc.sh stop

# Download new version (GitHub will notify you)
# Extract and replace files

# Start service
./svc.sh start
```

### View Logs

```powershell
# Real-time logs
Get-Content _diag\Runner_*.log -Wait -Tail 50

# Recent logs
Get-Content _diag\Runner_*.log -Tail 100
```

---

## Troubleshooting

### Runner not connecting?

1. Check internet connection
2. Check firewall (allow outbound HTTPS)
3. Restart runner service:
   ```powershell
   ./svc.sh restart
   ```

### Angel One still blocking?

1. Verify your IP hasn't changed:
   ```powershell
   curl ifconfig.me
   ```
2. If changed, contact Angel One to update whitelist
3. Consider getting static IP from ISP

### Workflow not running on self-hosted runner?

1. Check runner is online: GitHub repo → Settings → Actions → Runners
2. Verify workflow uses `runs-on: self-hosted`
3. Check runner labels match

### Python not found?

```powershell
# Install Python if not already installed
# Download from: https://www.python.org/downloads/

# Add to PATH
$env:Path += ";C:\Python311;C:\Python311\Scripts"
```

---

## Security Best Practices

### 1. Secure Your PC

- ✅ Keep Windows updated
- ✅ Use antivirus software
- ✅ Enable Windows Firewall
- ✅ Use strong passwords

### 2. Protect Credentials

- ✅ Store credentials in GitHub Secrets (not in code)
- ✅ Never commit credentials to repository
- ✅ Use environment variables

### 3. Monitor Activity

- ✅ Check GitHub Actions logs regularly
- ✅ Monitor Telegram alerts
- ✅ Review order logs in `radar_trades.json`

### 4. Backup

```powershell
# Backup your runner config
Copy-Item -Path "actions-runner\.runner" -Destination "backup\.runner"
Copy-Item -Path "actions-runner\.credentials" -Destination "backup\.credentials"
```

---

## Cost Breakdown

| Item | Cost |
|------|------|
| GitHub Self-Hosted Runner | **FREE** |
| Your PC (electricity) | ~₹100-200/month |
| Static IP from ISP (optional) | ₹0-500/month |
| **TOTAL** | **₹100-700/month** |

---

## Pros & Cons

### ✅ Pros
- Uses your home IP (Angel One allows it)
- No cloud VM needed
- Full control over environment
- Fast execution (local)
- FREE (except electricity)

### ❌ Cons
- PC must be running 24/7
- Uses your electricity
- If IP changes, need to update Angel One whitelist
- Single point of failure (if PC crashes)

---

## Alternative: Hybrid Approach

**Best of both worlds:**

1. Use **self-hosted runner** for Angel One orders (your IP)
2. Use **GitHub-hosted runner** for everything else (screener, updates)

```yaml
jobs:
  # Screener runs on GitHub servers
  run-screener:
    runs-on: ubuntu-latest
    steps:
      - name: Run screener
        run: python screener.py
  
  # Angel One orders run on your PC
  execute-trade:
    runs-on: self-hosted
    steps:
      - name: Place order
        run: python angel_trade.py
```

---

## Summary

✅ **Setup Time**: 30 minutes
✅ **Cost**: ₹100-700/month (electricity + optional static IP)
✅ **Reliability**: Depends on your PC uptime
✅ **IP**: Your home IP (Angel One allows it)
✅ **Automation**: Full GitHub Actions automation

Your Angel One orders will now run on your PC through GitHub Actions! 🚀
