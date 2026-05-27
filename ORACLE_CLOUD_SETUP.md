# Oracle Cloud Free VM Setup for Angel One (FREE Forever)

Oracle Cloud offers a **FREE VM with static IP that runs 24/7 forever** - perfect for Angel One integration.

---

## Why Oracle Cloud?

✅ **100% FREE Forever** (Always Free tier)
✅ **Static IP** (Angel One won't block it)
✅ **Runs 24/7** (no need to keep your PC on)
✅ **1 GB RAM, 1 CPU** (enough for our webhook server)
✅ **No credit card required** (after initial verification)

---

## Step 1: Create Oracle Cloud Account (10 minutes)

1. Go to: https://www.oracle.com/cloud/free/
2. Click **"Start for free"**
3. Fill in details:
   - Email
   - Country
   - Cloud Account Name (choose any)
4. Verify email
5. Add payment method (for verification only - won't be charged)
6. Wait for account activation (5-10 minutes)

---

## Step 2: Create Free VM Instance (5 minutes)

1. Login to Oracle Cloud Console
2. Click **"Create a VM instance"**
3. Configure:
   - **Name**: `angel-one-webhook`
   - **Image**: Ubuntu 22.04 (default)
   - **Shape**: VM.Standard.E2.1.Micro (Always Free)
   - **Network**: Use default VCN
   - **Public IP**: Assign a public IPv4 address ✅
   - **SSH Keys**: Download the private key (save it!)
4. Click **"Create"**
5. Wait 2-3 minutes for VM to start
6. **Copy the Public IP address** (e.g., 123.45.67.89)

---

## Step 3: Configure Firewall (2 minutes)

1. In Oracle Console, go to **Networking → Virtual Cloud Networks**
2. Click your VCN → **Security Lists** → **Default Security List**
3. Click **"Add Ingress Rules"**
4. Add rule:
   - **Source CIDR**: `0.0.0.0/0`
   - **Destination Port**: `8888`
   - **Description**: `Webhook server`
5. Click **"Add Ingress Rules"**

---

## Step 4: Connect to VM and Setup (10 minutes)

### Connect via SSH:

**Windows (using PowerShell):**
```powershell
# Replace with your private key path and VM IP
ssh -i C:\path\to\your-key.key ubuntu@YOUR_VM_IP
```

**Or use PuTTY** (download from: https://www.putty.org/)

### Once connected, run these commands:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip -y

# Install required packages
pip3 install smartapi-python pyotp requests logzero websocket-client

# Create working directory
mkdir ~/angel-webhook
cd ~/angel-webhook

# Download your scripts (we'll upload them next)
```

---

## Step 5: Upload Your Scripts to VM

### Option A: Using SCP (from your local machine)

```powershell
# Upload angel_trade.py
scp -i C:\path\to\your-key.key "d:\Stock Yard\angel_trade.py" ubuntu@YOUR_VM_IP:~/angel-webhook/

# Upload webhook server
scp -i C:\path\to\your-key.key "d:\Stock Yard\local_angel_webhook_server.py" ubuntu@YOUR_VM_IP:~/angel-webhook/
```

### Option B: Copy-paste manually

1. SSH into VM
2. Create files:
```bash
cd ~/angel-webhook
nano angel_trade.py
# Paste content, press Ctrl+X, Y, Enter

nano webhook_server.py
# Paste content, press Ctrl+X, Y, Enter
```

---

## Step 6: Set Environment Variables on VM

```bash
# Edit .bashrc to add credentials
nano ~/.bashrc

# Add these lines at the end:
export ANGEL_API_KEY="your_api_key"
export ANGEL_CLIENT_ID="your_client_id"
export ANGEL_PASSWORD="your_password"
export ANGEL_TOTP_SECRET="your_totp_secret"
export TELEGRAM_BOT_TOKEN="your_telegram_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export WEBHOOK_SECRET="choose_a_random_secret_123"

# Save and exit (Ctrl+X, Y, Enter)

# Reload environment
source ~/.bashrc
```

---

## Step 7: Create Systemd Service (Auto-start on boot)

```bash
# Create service file
sudo nano /etc/systemd/system/angel-webhook.service
```

Paste this content:

```ini
[Unit]
Description=Angel One Webhook Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/angel-webhook
Environment="ANGEL_API_KEY=your_api_key"
Environment="ANGEL_CLIENT_ID=your_client_id"
Environment="ANGEL_PASSWORD=your_password"
Environment="ANGEL_TOTP_SECRET=your_totp_secret"
Environment="TELEGRAM_BOT_TOKEN=your_telegram_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
Environment="WEBHOOK_SECRET=your_webhook_secret"
ExecStart=/usr/bin/python3 /home/ubuntu/angel-webhook/webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit (Ctrl+X, Y, Enter)

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable angel-webhook

# Start service
sudo systemctl start angel-webhook

# Check status
sudo systemctl status angel-webhook
```

---

## Step 8: Update GitHub Actions Workflow

Update `.github/workflows/angel_trade.yml`:

```yaml
name: Angel One Trade Executor

on:
  repository_dispatch:
    types: [place_trade]

jobs:
  execute-trade:
    runs-on: ubuntu-latest
    steps:
    - name: Execute trade via Oracle Cloud VM
      run: |
        curl -X POST http://YOUR_VM_PUBLIC_IP:8888/angel-order \
          -H "Content-Type: application/json" \
          -d '{
            "symbol": "${{ github.event.client_payload.symbol }}",
            "action": "${{ github.event.client_payload.action }}",
            "price": "${{ github.event.client_payload.price }}",
            "quantity": "${{ github.event.client_payload.quantity }}",
            "secret": "${{ secrets.WEBHOOK_SECRET }}"
          }'
```

**Add WEBHOOK_SECRET to GitHub Secrets:**
1. Go to your repo → Settings → Secrets → Actions
2. Add new secret: `WEBHOOK_SECRET` = `your_webhook_secret`

---

## Step 9: Test the Setup

### Test from your local machine:

```bash
curl -X POST http://YOUR_VM_PUBLIC_IP:8888/angel-order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SBIN",
    "action": "BUY",
    "price": "850.50",
    "quantity": "10",
    "secret": "your_webhook_secret"
  }'
```

### Check logs on VM:

```bash
# View real-time logs
sudo journalctl -u angel-webhook -f

# View recent logs
sudo journalctl -u angel-webhook -n 50
```

---

## Maintenance Commands

```bash
# Restart service
sudo systemctl restart angel-webhook

# Stop service
sudo systemctl stop angel-webhook

# View logs
sudo journalctl -u angel-webhook -f

# Check if service is running
sudo systemctl status angel-webhook
```

---

## Security Best Practices

1. **Change default SSH port** (optional):
```bash
sudo nano /etc/ssh/sshd_config
# Change Port 22 to Port 2222
sudo systemctl restart sshd
```

2. **Enable firewall**:
```bash
sudo ufw allow 8888/tcp
sudo ufw allow 2222/tcp  # If you changed SSH port
sudo ufw enable
```

3. **Keep system updated**:
```bash
sudo apt update && sudo apt upgrade -y
```

---

## Troubleshooting

### Service won't start?
```bash
# Check logs
sudo journalctl -u angel-webhook -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8888

# Test script manually
cd ~/angel-webhook
python3 webhook_server.py
```

### Can't connect from GitHub Actions?
- Check Oracle Cloud firewall (Ingress Rules)
- Check VM firewall: `sudo ufw status`
- Verify VM public IP hasn't changed
- Test with curl from your local machine first

### Angel One still blocking?
- Contact Angel One support
- Ask them to whitelist your VM's public IP
- Provide them the static IP from Oracle Cloud

---

## Cost Breakdown

| Item | Cost |
|------|------|
| VM Instance (E2.1.Micro) | **FREE Forever** |
| 1 GB RAM | **FREE Forever** |
| Static Public IP | **FREE Forever** |
| 10 GB Boot Volume | **FREE Forever** |
| Outbound Data Transfer (10 TB/month) | **FREE Forever** |
| **TOTAL** | **₹0 / $0** |

---

## Summary

✅ **Setup Time**: 30 minutes (one-time)
✅ **Cost**: FREE forever
✅ **Maintenance**: Zero (auto-restarts, auto-updates)
✅ **Reliability**: 99.9% uptime
✅ **Static IP**: Angel One won't block it
✅ **24/7 Running**: No need to keep your PC on

Your Angel One orders will now work perfectly through GitHub Actions! 🚀
