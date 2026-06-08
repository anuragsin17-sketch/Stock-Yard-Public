#!/bin/bash
# Run this directly on EC2 - fixes and deploys the Angel API service

echo "🚀 Deploying Angel One API to EC2..."

# Step 1: Pull latest code
cd /home/ubuntu
git pull origin main

# Step 2: Stop old service if running
sudo systemctl stop angel-api 2>/dev/null || true

# Step 3: Copy new service file
sudo cp angel-api.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/angel-api.service

# Step 4: Reload systemd
sudo systemctl daemon-reload

# Step 5: Enable and start service
sudo systemctl enable angel-api
sudo systemctl start angel-api

# Step 6: Wait and check status
sleep 2
echo ""
echo "Service Status:"
sudo systemctl status angel-api

# Step 7: Test health endpoint
echo ""
echo "Testing health endpoint..."
curl -s http://localhost:5000/health | python3 -m json.tool || echo "Health check failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "View live logs:"
echo "  sudo journalctl -u angel-api -f"
echo ""
echo "Check from your PC:"
echo "  curl http://32.194.58.75:5000/health"
