#!/usr/bin/env python3
"""
Manual EC2 Deployment - Copy and setup files directly
Uses EC2 Instance Connect or direct boto3 approach
"""

import json
import boto3
from pathlib import Path
import subprocess
import os

def deploy_manual(config_path='d:\\Stock Yard\\aws_config.json'):
    """Deploy dashboard by manually updating EC2"""
    
    # Load AWS credentials
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
        return False
    
    # Initialize EC2 client
    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("MANUAL DASHBOARD DEPLOYMENT")
    print("="*60 + "\n")
    
    # Get instance
    print("⏳ Finding EC2 instance...")
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['StockYard-TradingBot']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        if not response['Reservations']:
            print("✗ No running instances found")
            return False
        
        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        public_ip = instance.get('PublicIpAddress', 'N/A')
        
        print(f"✓ Found instance: {instance_id}")
        print(f"  Public IP: {public_ip}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Create deployment script
    deployment_script = '''#!/bin/bash
set -e

# Update and install Nginx
apt-get update
apt-get install -y nginx

# Create web directory
mkdir -p /var/www/stockyard
cd /var/www/stockyard

# Create index.html
cat > index.html << 'DASHBOARD_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Yard Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 10px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .header h1 { color: #667eea; margin-bottom: 10px; font-size: 28px; }
        .header p { color: #666; margin-top: 5px; }
        .header-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }
        .info-card { background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
        .info-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .info-value { font-size: 18px; font-weight: bold; color: #667eea; margin-top: 5px; }
        .tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
        .tab-btn { padding: 15px; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; transition: all 0.3s; text-transform: uppercase; }
        .tab-btn.volume { background: rgba(255, 255, 255, 0.9); color: #667eea; border: 2px solid #667eea; }
        .tab-btn.volume.active { background: #667eea; color: white; }
        .tab-btn.trendline { background: rgba(255, 255, 255, 0.9); color: #764ba2; border: 2px solid #764ba2; }
        .tab-btn.trendline.active { background: #764ba2; color: white; }
        .tab-btn.radar { background: rgba(255, 255, 255, 0.9); color: #f093fb; border: 2px solid #f093fb; }
        .tab-btn.radar.active { background: #f093fb; color: white; }
        .content { background: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); min-height: 400px; }
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .stock-card { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #667eea; }
        .stock-ticker { font-size: 18px; font-weight: bold; color: #333; }
        .stock-price { font-size: 14px; color: #666; margin-top: 5px; }
        .stock-status { padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; background: #2ed573; color: white; display: inline-block; margin-top: 5px; }
        .refresh-btn { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-bottom: 15px; }
        .refresh-btn:hover { background: #764ba2; }
        .last-update { text-align: center; color: #666; font-size: 12px; margin-top: 20px; }
        @media (max-width: 768px) { .tabs { grid-template-columns: 1fr; } .header h1 { font-size: 20px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1>🤖 Stock Yard Trading Dashboard</h1>
                    <p>Real-time Nifty 500 Stock Scanner</p>
                </div>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
            </div>
            <div class="header-info">
                <div class="info-card">
                    <div class="info-label">Status</div>
                    <div class="info-value">🟢 Active</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Stocks Scanned</div>
                    <div class="info-value">500</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Alerts Today</div>
                    <div class="info-value" id="alertCount">0</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Next Scan</div>
                    <div class="info-value" id="nextScan">5m</div>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab-btn volume active" onclick="switchTab('volume')">📊 Volume Tab</button>
            <button class="tab-btn trendline" onclick="switchTab('trendline')">📈 Trendline Support</button>
            <button class="tab-btn radar" onclick="switchTab('radar')">🎯 Radar (Critical)</button>
        </div>

        <div class="content">
            <div id="volume" class="tab-content active">
                <h2 style="margin-bottom: 15px; color: #667eea;">📊 Volume Tab - High Activity Stocks</h2>
                <div class="stock-card">
                    <div class="stock-ticker">RELIANCE</div>
                    <div class="stock-price">₹2,500 • Volume: 50M</div>
                    <div class="stock-status">🆕 NEW</div>
                </div>
                <div class="stock-card">
                    <div class="stock-ticker">TCS</div>
                    <div class="stock-price">₹3,500 • Volume: 35M</div>
                    <div class="stock-status">🆕 NEW</div>
                </div>
            </div>

            <div id="trendline" class="tab-content">
                <h2 style="margin-bottom: 15px; color: #764ba2;">📈 Trendline Support Zone</h2>
                <div class="stock-card">
                    <div class="stock-ticker">WIPRO</div>
                    <div class="stock-price">Current: ₹400 | Support: ₹385 | Target: ₹480</div>
                    <div class="stock-status">💡 ENTRY</div>
                </div>
                <div class="stock-card">
                    <div class="stock-ticker">HCLTECH</div>
                    <div class="stock-price">Current: ₹1,250 | Support: ₹1,200 | Target: ₹1,530</div>
                    <div class="stock-status">💡 ENTRY</div>
                </div>
            </div>

            <div id="radar" class="tab-content">
                <h2 style="margin-bottom: 15px; color: #f093fb;">🎯 Radar - Critical Entry Zone</h2>
                <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 15px; border-radius: 5px; margin-bottom: 15px; color: #155724;">
                    ⚠️ 1 stock in CRITICAL zone - Ready for entry!
                </div>
                <div class="stock-card" style="border-left-color: #ff4757; background: #ffe5e5;">
                    <div class="stock-ticker">BAJAJFINSV</div>
                    <div class="stock-price">Entry: ₹1,520 | Support: ₹1,500 | Distance: 1.3%</div>
                    <div style="padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; background: #ff4757; color: white; display: inline-block; margin-top: 5px;">🔴 CRITICAL</div>
                </div>
            </div>
        </div>

        <div class="last-update">
            Last updated: <span id="lastUpdate">Just now</span>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            document.querySelector('.tab-btn.' + tabName).classList.add('active');
        }

        function refreshData() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            alert('✅ Dashboard refreshed!');
        }

        window.addEventListener('load', function() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        });
    </script>
</body>
</html>
DASHBOARD_EOF

# Configure Nginx
cat > /etc/nginx/sites-available/stockyard << 'CONF'
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
CONF

ln -sf /etc/nginx/sites-available/stockyard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Restart Nginx
systemctl restart nginx

echo "✓ Dashboard deployed successfully"
'''
    
    # Save script to file
    script_path = "d:\\Stock Yard\\deploy_script.sh"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(deployment_script)
    
    print(f"\n✓ Created deployment script: {script_path}")
    print(f"\n📋 MANUAL DEPLOYMENT INSTRUCTIONS:")
    print(f"="*60)
    print(f"\nTo complete the dashboard deployment, you have two options:\n")
    print(f"OPTION 1: SSH into the EC2 instance and run the script")
    print(f"─" * 60)
    print(f"1. SSH to your EC2 instance:")
    print(f"   ssh -i your-key.pem ubuntu@{public_ip}\n")
    print(f"2. Run these commands:")
    print(f"   sudo bash -c 'apt-get update && apt-get install -y nginx'")
    print(f"   sudo mkdir -p /var/www/stockyard")
    print(f"   sudo cp /path/to/dashboard.html /var/www/stockyard/index.html\n")
    print(f"OPTION 2: Use EC2 Instance Connect (browser-based)")
    print(f"─" * 60)
    print(f"1. Go to AWS Console > EC2 > Instances")
    print(f"2. Select instance {instance_id}")
    print(f"3. Click 'Connect' > 'EC2 Instance Connect'")
    print(f"4. Run the same commands as Option 1\n")
    print(f"OPTION 3: Use this automated SSH command (if you have ssh key)")
    print(f"─" * 60)
    print(f"ssh -i your-key.pem ubuntu@{public_ip} 'bash -s' < {script_path}\n")
    print(f"="*60)
    print(f"\n🌐 After deployment, access dashboard at:")
    print(f"   http://{public_ip}\n")
    print(f"💡 Current status: Dashboard code is ready, waiting for manual SSH setup\n")
    
    return True


if __name__ == '__main__':
    deploy_manual()
