#!/bin/bash

# Telegram Webhook Deployment Script for EC2
# Run this on your EC2 instance with: bash deploy_telegram_webhook.sh

set -e

echo "=========================================="
echo "📦 TELEGRAM WEBHOOK DEPLOYMENT"
echo "=========================================="

# Variables
EC2_IP="32.194.58.75"
REPO_DIR="/home/ubuntu/stock-yard"
SERVICE_NAME="telegram-webhook"
WEBHOOK_PORT="8443"

# Step 1: Prepare directories
echo "📁 Setting up directories..."
mkdir -p $REPO_DIR
cd $REPO_DIR

# Step 2: Install dependencies
echo "📥 Installing Python dependencies..."
pip3 install -q flask requests pyopenssl --upgrade

# Step 3: Generate self-signed SSL certificate (valid for 365 days)
echo "🔐 Generating SSL certificate..."
mkdir -p /home/ubuntu/ssl
cd /home/ubuntu/ssl

if [ ! -f telegram.crt ]; then
    openssl req -x509 -newkey rsa:4096 -keyout telegram.key -out telegram.crt -days 365 -nodes \
        -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=StockYard/CN=$EC2_IP"
    echo "✅ SSL certificate generated"
else
    echo "⚠️  SSL certificate already exists"
fi

# Set permissions
chmod 600 telegram.key
chmod 644 telegram.crt

# Step 4: Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << 'EOF'
[Unit]
Description=Stock Yard Telegram Webhook
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stock-yard
Environment="TELEGRAM_BOT_TOKEN=8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
Environment="TELEGRAM_CHAT_ID=8901309420"
Environment="WEBHOOK_URL=https://32.194.58.75:8443/webhook/telegram"
ExecStart=/usr/bin/python3 /home/ubuntu/stock-yard/telegram_webhook_simple.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
StandardInput=null

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "✅ Systemd service created"

# Step 5: Start the service
echo "🚀 Starting service..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

sleep 2

# Step 6: Verify service is running
echo "🔍 Checking service status..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start. Check logs:"
    sudo journalctl -u $SERVICE_NAME -n 20
    exit 1
fi

# Step 7: Register webhook with Telegram
echo "📡 Registering webhook with Telegram..."
sleep 2

curl -k -X POST https://localhost:$WEBHOOK_PORT/register-webhook \
    -H "Content-Type: application/json" \
    -d '{}' \
    2>/dev/null || echo "⚠️  Webhook registration request sent"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Service Details:"
echo "  Name: $SERVICE_NAME"
echo "  Status: $(sudo systemctl is-active $SERVICE_NAME)"
echo "  Logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Next Steps:"
echo "  1. Send a test alert from GitHub Actions"
echo "  2. Click 'Confirm Trade' button in Telegram"
echo "  3. Check logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Troubleshooting:"
echo "  - View logs: sudo journalctl -u $SERVICE_NAME -n 50"
echo "  - Restart: sudo systemctl restart $SERVICE_NAME"
echo "  - Stop: sudo systemctl stop $SERVICE_NAME"
echo "=========================================="
