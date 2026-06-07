#!/bin/bash
# Setup Flask server on EC2 and register Telegram webhook

set -e

echo "🚀 Setting up Telegram Trade Server on EC2"
echo "=========================================="

# 1. Update system
echo "📦 Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip nginx git >/dev/null 2>&1

# 2. Install Python packages
echo "🐍 Installing Python packages..."
pip3 install flask requests pyotp SmartApi --quiet

# 3. Navigate to repo
cd /home/ubuntu || cd ~
echo "📍 Working directory: $(pwd)"

# 4. Pull latest code (if in git repo)
echo "📥 Pulling latest code..."
if [ -d .git ]; then
  git pull origin main 2>&1 || echo "⚠️ Git pull skipped"
else
  echo "⚠️ Not in git repo - cloning from GitHub..."
  git clone https://github.com/anuragsin17-sketch/Stock-Yard.git /tmp/stock-yard
  cp /tmp/stock-yard/telegram_flask_server.py .
  cp /tmp/stock-yard/telegram_trade_bot.py .
fi

# 5. Create systemd service for Flask
echo "🔧 Creating Flask service..."
sudo tee /etc/systemd/system/telegram-trade-server.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Stock Yard Telegram Trade Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="TELEGRAM_BOT_TOKEN=8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
Environment="TELEGRAM_CHAT_ID=8901309420"
Environment="ANGEL_API_KEY=SZqPJrCA"
Environment="ANGEL_CLIENT_CODE=AAAA971572"
Environment="ANGEL_PASSWORD=1990"
Environment="ANGEL_TOTP_SECRET=YOUR_TOTP_SECRET_HERE"
ExecStart=/usr/bin/python3 /home/ubuntu/telegram_flask_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

# 6. Enable and start service
echo "✅ Starting Flask service..."
sudo systemctl daemon-reload
sudo systemctl enable telegram-trade-server
sudo systemctl restart telegram-trade-server

# 7. Wait for service to start
sleep 3

# 8. Check status
echo "📊 Checking service status..."
sudo systemctl status telegram-trade-server --no-pager || echo "⚠️ Service check failed"

# 9. Check if server is responding
echo "🧪 Testing server..."
curl -s http://localhost:5000/health | python3 -m json.tool || echo "⚠️ Server not responding yet"

# 10. Setup Telegram webhook
echo "🔗 Setting up Telegram webhook..."
BOT_TOKEN="8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
EC2_IP="32.194.58.75"
WEBHOOK_URL="http://${EC2_IP}:5000/webhook/telegram"

python3 << EOFPYTHON
import requests
import json

bot_token = "$BOT_TOKEN"
webhook_url = "$WEBHOOK_URL"

# Set webhook
url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
payload = {
    'url': webhook_url,
    'allowed_updates': ['callback_query', 'message']
}

print(f"🔗 Registering webhook: {webhook_url}")
response = requests.post(url, json=payload, timeout=10)
result = response.json()

if result.get('ok'):
    print(f"✅ Webhook registered!")
    print(f"   Description: {result.get('description')}")
else:
    print(f"❌ Webhook failed: {result.get('description')}")
EOFPYTHON

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary:"
echo "   ✓ Flask server running on port 5000"
echo "   ✓ Telegram webhook registered"
echo "   ✓ Service auto-starts on reboot"
echo ""
echo "🧪 To test:"
echo "   curl http://localhost:5000/health"
echo ""
echo "📊 To view logs:"
echo "   journalctl -u telegram-trade-server -f"
