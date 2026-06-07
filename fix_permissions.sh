#!/bin/bash
# Fix permissions for Stock Yard dashboard

echo "Fixing permissions..."

# Run as root to fix permissions
sudo bash << 'SUDOEOF'

# Create directory with proper permissions
mkdir -p /var/www/stockyard
chmod 755 /var/www/stockyard
chown -R www-data:www-data /var/www/stockyard

# Verify
ls -la /var/www/stockyard

echo "Permissions fixed!"

SUDOEOF
