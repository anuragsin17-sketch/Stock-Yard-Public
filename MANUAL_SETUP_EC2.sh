#!/bin/bash
# Manual setup script for Stock Yard Dashboard
# Run this on the EC2 instance via EC2 Instance Connect

set -e

echo "=========================================="
echo "STOCK YARD DASHBOARD SETUP"
echo "=========================================="

# Update apt
echo ""
echo "Step 1: Updating system..."
apt-get update -qq 2>&1 | tail -5
apt-get upgrade -y -qq 2>&1 | tail -3

# Install Nginx
echo ""
echo "Step 2: Installing Nginx..."
apt-get install -y nginx 2>&1 | tail -3

# Create web directory
echo ""
echo "Step 3: Creating web directory..."
mkdir -p /var/www/stockyard
chown -R www-data:www-data /var/www/stockyard
chmod -R 755 /var/www/stockyard

# Configure Nginx
echo ""
echo "Step 4: Configuring Nginx..."
cat > /etc/nginx/sites-available/stockyard << 'CONFEOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/stockyard;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}
CONFEOF

ln -sf /etc/nginx/sites-available/stockyard /etc/nginx/sites-enabled/ 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test Nginx config
nginx -t

# Restart Nginx
echo ""
echo "Step 5: Starting Nginx..."
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=========================================="
echo "READY FOR DASHBOARD HTML"
echo "=========================================="
echo ""
echo "Next: Copy the content from dashboard.html"
echo "and run:"
echo ""
echo "cat > /var/www/stockyard/index.html << 'EOF'"
echo "[paste HTML content here]"
echo "EOF"
echo ""
echo "Then restart Nginx:"
echo "sudo systemctl restart nginx"
echo ""
echo "=========================================="
