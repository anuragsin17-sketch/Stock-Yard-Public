#!/bin/bash
# Quick setup script for Angel One API on EC2
# Run this on your EC2 instance: bash setup_angel_api_ec2.sh

set -e

echo "=========================================="
echo "Angel One API Handler - EC2 Setup"
echo "=========================================="

# Step 1: Update system
echo "[1/6] Updating system packages..."
sudo apt-get update > /dev/null 2>&1
sudo apt-get install -y python3-pip git curl > /dev/null 2>&1

# Step 2: Install Python dependencies
echo "[2/6] Installing Python dependencies..."
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install Flask==2.3.2 requests pyotp smartapi-python==1.3.7 > /dev/null 2>&1

# Step 3: Verify installation
echo "[3/6] Verifying dependencies..."
python3 -c "from flask import Flask; from SmartApi import SmartConnect; print('✓ All dependencies installed')" || {
    echo "✗ Dependency installation failed"
    exit 1
}

# Step 4: Copy service file
echo "[4/6] Setting up systemd service..."
if [ ! -f "angel-api.service" ]; then
    echo "✗ angel-api.service not found in current directory"
    exit 1
fi

sudo cp angel-api.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/angel-api.service

# Step 5: Verify script exists
echo "[5/6] Verifying service script..."
if [ ! -f "angel_order_handler.py" ]; then
    echo "✗ angel_order_handler.py not found in current directory"
    exit 1
fi

# Step 6: Start service
echo "[6/6] Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable angel-api
sudo systemctl start angel-api

# Verify
sleep 2
if sudo systemctl is-active --quiet angel-api; then
    echo "✓ Service started successfully!"
else
    echo "✗ Service failed to start. Check logs:"
    sudo journalctl -u angel-api -n 10
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service Status:"
sudo systemctl status angel-api --no-pager
echo ""
echo "Health Check:"
curl -s http://localhost:5000/health | python3 -m json.tool
echo ""
echo "Next Steps:"
echo "1. Test from your PC: curl http://32.194.58.75:5000/health"
echo "2. Update dashboard to use http://32.194.58.75:5000"
echo "3. Check logs: sudo journalctl -u angel-api -f"
echo ""
