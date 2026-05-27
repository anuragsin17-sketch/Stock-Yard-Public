# Angel One IP Restriction Bypass - FREE Solutions

Angel One blocks GitHub Actions due to dynamic IPs. Here are **100% FREE** solutions:

---

## ✅ Solution 1: Cloudflare Tunnel (RECOMMENDED - FREE)

Cloudflare Tunnel creates a secure connection from your local machine to the internet.

### Setup Steps:

#### 1. Install Cloudflare Tunnel (One-time)
```bash
# Windows
# Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
# Or use winget:
winget install --id Cloudflare.cloudflared
```

#### 2. Start Local Webhook Server
```bash
# Set your Angel One credentials
set ANGEL_API_KEY=your_key
set ANGEL_CLIENT_ID=your_client_id
set ANGEL_PASSWORD=your_password
set ANGEL_TOTP_SECRET=your_totp_secret

# Start the webhook server
python local_angel_webhook_server.py
```

#### 3. Start Cloudflare Tunnel (in another terminal)
```bash
cloudflared tunnel --url http://localhost:8888
```

You'll get a public URL like: `https://abc-xyz-123.trycloudflare.com`

#### 4. Update GitHub Actions Workflow

Replace the Angel One execution step in `.github/workflows/angel_trade.yml`:

```yaml
- name: Execute trade via local webhook
  run: |
    curl -X POST https://your-tunnel-url.trycloudflare.com/angel-order \
      -H "Content-Type: application/json" \
      -d '{
        "symbol": "${{ github.event.client_payload.symbol }}",
        "action": "${{ github.event.client_payload.action }}",
        "price": "${{ github.event.client_payload.price }}",
        "quantity": "${{ github.event.client_payload.quantity }}",
        "secret": "${{ secrets.WEBHOOK_SECRET }}"
      }'
```

#### 5. Keep Running
- Keep both terminals running (webhook server + cloudflare tunnel)
- Orders from GitHub Actions will route through your local machine
- Your local machine has a static IP that Angel One allows

---

## ✅ Solution 2: ngrok (FREE Tier - 8 hours/day)

Similar to Cloudflare but with time limits on free tier.

### Setup:
```bash
# 1. Install ngrok
# Download from: https://ngrok.com/download

# 2. Start webhook server
python local_angel_webhook_server.py

# 3. Start ngrok (in another terminal)
ngrok http 8888

# 4. Use the ngrok URL in GitHub Actions
```

**Limitation**: Free tier disconnects after 8 hours, need to restart.

---

## ✅ Solution 3: Run from Local Machine Only (Simplest)

Skip GitHub Actions entirely for Angel One orders.

### Setup:

#### 1. Create a local order trigger script:

```python
# local_place_order.py
import os
import subprocess
import sys

symbol = input("Stock Symbol: ").upper()
action = input("Action (BUY/SELL): ").upper()
price = input("Entry Price: ")
quantity = input("Quantity: ")

os.environ['TRADE_SYMBOL'] = symbol
os.environ['TRADE_ACTION'] = action
os.environ['TRADE_PRICE'] = price
os.environ['TRADE_QUANTITY'] = quantity

subprocess.run(['python', 'angel_trade.py'])
```

#### 2. Run locally:
```bash
python local_place_order.py
```

**Pros**: No IP issues, simple
**Cons**: Must run manually from your machine

---

## ✅ Solution 4: Oracle Cloud Free Tier VM (FREE Forever)

Oracle Cloud offers a free VM with static IP forever.

### Setup:
1. Sign up: https://www.oracle.com/cloud/free/
2. Create a free VM (Always Free tier)
3. Install Python and dependencies
4. Run webhook server on VM
5. Use VM's static IP in GitHub Actions

**Pros**: Static IP, runs 24/7, FREE forever
**Cons**: Initial setup takes 30 minutes

---

## Comparison

| Solution | Cost | Setup Time | Reliability | Best For |
|----------|------|------------|-------------|----------|
| **Cloudflare Tunnel** | FREE | 5 min | ⭐⭐⭐⭐⭐ | Most users |
| **ngrok** | FREE (8h limit) | 5 min | ⭐⭐⭐ | Testing |
| **Local Only** | FREE | 2 min | ⭐⭐⭐⭐⭐ | Manual trading |
| **Oracle Cloud VM** | FREE | 30 min | ⭐⭐⭐⭐⭐ | 24/7 automation |

---

## Recommended: Cloudflare Tunnel

**Why?**
- ✅ 100% FREE
- ✅ No time limits
- ✅ Easy setup (5 minutes)
- ✅ Reliable
- ✅ No account required
- ✅ Works with dynamic IPs

**How it works:**
```
GitHub Actions → Cloudflare Tunnel → Your Local Machine → Angel One API
                 (Public URL)        (Static IP allowed)
```

Your local machine has a static IP that Angel One allows, so orders work perfectly!

---

## Need Help?

1. **Cloudflare Tunnel not working?**
   - Make sure webhook server is running first
   - Check firewall allows port 8888
   - Try a different port if 8888 is blocked

2. **Angel One still blocking?**
   - Verify your local IP is whitelisted with Angel One
   - Contact Angel One support to whitelist your home IP

3. **Want 24/7 automation?**
   - Use Oracle Cloud Free VM (static IP, runs forever, FREE)
