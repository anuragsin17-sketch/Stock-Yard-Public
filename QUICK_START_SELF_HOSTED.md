# Quick Start: Self-Hosted Runner for Angel One

## 🚀 3-Step Setup (15 minutes)

### Step 1: Check Your IP & Whitelist with Angel One

```powershell
# Check your public IP
curl ifconfig.me
```

**Contact Angel One support** and ask them to whitelist this IP for API access.

---

### Step 2: Install GitHub Runner

**Run as Administrator:**

```powershell
# Navigate to your project
cd "d:\Stock Yard"

# Run setup script
powershell -ExecutionPolicy Bypass -File setup_github_runner.ps1
```

**When prompted:**
1. Repository URL: `https://github.com/YOUR_USERNAME/Stock-Yard`
2. Token: Get from https://github.com/YOUR_USERNAME/Stock-Yard/settings/actions/runners/new

The script will:
- ✅ Download and install GitHub runner
- ✅ Configure it for your repository
- ✅ Install as Windows service (auto-starts with PC)
- ✅ Start the service

---

### Step 3: Verify & Test

**Check runner is online:**
1. Go to: https://github.com/YOUR_USERNAME/Stock-Yard/settings/actions/runners
2. You should see "angel-one-runner" with status: **Idle** (green)

**Test with an order:**
```powershell
# Using GitHub CLI (install from: https://cli.github.com/)
gh api repos/YOUR_USERNAME/Stock-Yard/dispatches `
  -f event_type=place_trade `
  -f client_payload[symbol]=SBIN `
  -f client_payload[action]=BUY `
  -f client_payload[price]=850.50 `
  -f client_payload[quantity]=1
```

**Check logs:**
```powershell
cd C:\actions-runner
Get-Content _diag\Runner_*.log -Tail 50 -Wait
```

---

## ✅ Done!

Your PC is now a self-hosted GitHub runner. Angel One orders will run on your PC (using your whitelisted IP).

---

## Daily Usage

**No action needed!** The runner runs automatically in the background.

When you trigger an order from your dashboard:
1. GitHub sends the order to your PC
2. Your PC executes `angel_trade.py`
3. Order goes to Angel One (using your whitelisted IP)
4. You get Telegram notification

---

## Troubleshooting

### Runner not showing as online?

```powershell
cd C:\actions-runner
.\svc.sh status
.\svc.sh restart
```

### Angel One still blocking?

1. Verify your IP hasn't changed:
   ```powershell
   curl ifconfig.me
   ```
2. If changed, contact Angel One to update whitelist

### View runner logs:

```powershell
cd C:\actions-runner
Get-Content _diag\Runner_*.log -Tail 100
```

---

## Uninstall

```powershell
cd C:\actions-runner
.\svc.sh stop
.\svc.sh uninstall
.\config.cmd remove --token YOUR_TOKEN
cd ..
Remove-Item -Recurse -Force C:\actions-runner
```

---

## Cost

- GitHub Runner: **FREE**
- Electricity: ~₹100-200/month (PC running 24/7)
- Static IP (optional): ₹0-500/month from ISP

**Total: ₹100-700/month**
