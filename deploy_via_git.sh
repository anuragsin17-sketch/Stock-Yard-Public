#!/bin/bash
# Deploy from GitHub to EC2

set -e

echo "🚀 Stock Yard Telegram Bot Deployment"
echo "======================================"

# Navigate to repo
cd /home/ubuntu || cd ~

# Pull latest code from GitHub
echo "📥 Pulling from GitHub..."
git pull origin main || echo "⚠️ Git pull attempted"

# Make sure dependencies are installed
echo "📦 Installing dependencies..."
pip3 install requests --quiet 2>/dev/null || sudo pip3 install requests --quiet

# List bot files
echo "📋 Bot files:"
ls -la telegram_trade_bot.py telegram_webhook_server.py deploy_bot.sh 2>/dev/null || echo "⚠️ Some files missing"

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Stock Yard Telegram Bot Poller
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="TELEGRAM_BOT_TOKEN=8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
Environment="TELEGRAM_CHAT_ID=8901309420"
Environment="TRADING_MODE=live"
ExecStart=/usr/bin/python3 /home/ubuntu/telegram_webhook_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Enable and start service
echo "✅ Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl restart telegram-bot

# Check status
echo "📊 Checking service status..."
sleep 2
sudo systemctl status telegram-bot --no-pager

echo "✅ Deployment complete!"
