#!/bin/bash
# Deploy the fixed Angel API to EC2

echo "Deploying Angel API fix to EC2..."
echo "=================================="

# Copy the new handler (no Flask dependency)
echo "1. Copying new handler to EC2..."
scp -i ~/stock-yard-key.pem angel_order_handler_http.py ubuntu@32.194.58.75:/home/ubuntu/

# Copy updated service file
echo "2. Updating systemd service..."
scp -i ~/stock-yard-key.pem angel-api.service ubuntu@32.194.58.75:/tmp/

# SSH to EC2 and update service
echo "3. Installing and restarting service..."
ssh -i ~/stock-yard-key.pem ubuntu@32.194.58.75 << 'EOF'
    # Copy service file to systemd
    sudo cp /tmp/angel-api.service /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Restart service
    sudo systemctl restart angel-api
    
    # Check status
    sleep 2
    sudo systemctl status angel-api
    
    # Show last logs
    echo ""
    echo "Last logs:"
    sudo journalctl -u angel-api -n 10
EOF

echo ""
echo "Deployment complete!"
echo "Check if service is running: curl http://32.194.58.75:5000/health"
