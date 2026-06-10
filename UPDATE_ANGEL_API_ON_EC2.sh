#!/bin/bash
# Update Angel Order Handler on EC2 with CORS support

echo "📤 Updating Angel Order Handler on EC2..."
echo "==========================================="

# Variables
EC2_USER="ubuntu"
EC2_IP="32.194.58.75"
LOCAL_FILE="angel_order_handler.py"
REMOTE_PATH="/home/ubuntu/angel_order_handler.py"

# 1. Install flask-cors on EC2
echo ""
echo "1️⃣  Installing flask-cors..."
scp -i stock-yard-key.pem $LOCAL_FILE $EC2_USER@$EC2_IP:/tmp/

ssh -i stock-yard-key.pem $EC2_USER@$EC2_IP << 'EOF'
echo "Installing flask-cors..."
pip3 install flask-cors

echo "Stopping angel-api service..."
sudo systemctl stop angel-api

echo "Backing up old version..."
sudo cp /home/ubuntu/angel_order_handler.py /home/ubuntu/angel_order_handler.py.backup

echo "Copying new version..."
sudo cp /tmp/angel_order_handler.py /home/ubuntu/angel_order_handler.py
sudo chown ubuntu:ubuntu /home/ubuntu/angel_order_handler.py

echo "Starting service..."
sudo systemctl start angel-api

echo "Checking status..."
sudo systemctl status angel-api --no-pager

echo "Testing health endpoint..."
sleep 2
curl http://localhost:5000/health

echo ""
echo "✅ Update complete!"
EOF

echo ""
echo "==========================================="
echo "✅ Angel Order Handler updated with CORS support"
echo ""
