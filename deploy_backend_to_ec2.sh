#!/bin/bash
# Deploy Stock Yard Backend to EC2

echo "==============================================="
echo "Stock Yard Angel One Order API - EC2 Deployment"
echo "==============================================="

# Update system
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv curl wget -qq

# Install Python packages
pip3 install flask requests pyotp smartapi-python --quiet 2>/dev/null

# Download the backend script from GitHub
cd /home/ubuntu
git clone https://github.com/anuragsin17-sketch/Stock-Yard.git || cd Stock-Yard && git pull

# Create systemd service for the Flask backend
echo "Creating systemd service..."
sudo tee /etc/systemd/system/angel-api.service > /dev/null << 'EOF'
[Unit]
Description=Stock Yard Angel One Order API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Stock-Yard
Environment="ANGEL_API_KEY=SZqPJrCA"
Environment="ANGEL_CLIENT_ID=AAAA971572"
Environment="ANGEL_PASSWORD=1990"
Environment="ANGEL_TOTP_SECRET=75HLXE2L3L7NASX47RCIJTKEKM"
Environment="TELEGRAM_BOT_TOKEN=8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
Environment="TELEGRAM_CHAT_ID=8901309420"
ExecStart=/usr/bin/python3 /home/ubuntu/Stock-Yard/angel_order_handler.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable angel-api
sudo systemctl start angel-api

# Check status
echo ""
echo "==============================================="
echo "Service Status:"
sudo systemctl status angel-api

echo ""
echo "==============================================="
echo "DEPLOYMENT COMPLETE!"
echo "Backend is running on: http://32.194.58.75:5000"
echo ""
echo "View logs with: sudo journalctl -u angel-api -f"
echo "==============================================="
