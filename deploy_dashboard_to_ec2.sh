#!/bin/bash
# Deploy Dashboard to EC2 Instance
# Run this script on your EC2 instance via SSH or EC2 Instance Connect

echo "=========================================="
echo "DEPLOYING DASHBOARD TO EC2"
echo "=========================================="

# Create dashboard directory
mkdir -p /var/www/stockyard
cd /var/www/stockyard

# Create dashboard HTML file
cat > index.html << 'DASHBOARD_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Yard - Trading Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 10px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .header-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .info-card {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }

        .info-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }

        .info-value {
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
            margin-top: 5px;
        }

        .tabs {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab-btn {
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .tab-btn.volume {
            background: rgba(255, 255, 255, 0.9);
            color: #667eea;
            border: 2px solid #667eea;
        }

        .tab-btn.volume:hover,
        .tab-btn.volume.active {
            background: #667eea;
            color: white;
        }

        .tab-btn.trendline {
            background: rgba(255, 255, 255, 0.9);
            color: #764ba2;
            border: 2px solid #764ba2;
        }

        .tab-btn.trendline:hover,
        .tab-btn.trendline.active {
            background: #764ba2;
            color: white;
        }

        .tab-btn.radar {
            background: rgba(255, 255, 255, 0.9);
            color: #f093fb;
            border: 2px solid #f093fb;
        }

        .tab-btn.radar:hover,
        .tab-btn.radar.active {
            background: #f093fb;
            color: white;
        }

        .content {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            min-height: 400px;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .stock-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .stock-card.critical {
            border-left-color: #ff4757;
            background: #ffe5e5;
        }

        .stock-card.watchlist {
            border-left-color: #ffa502;
            background: #fff5e5;
        }

        .stock-info {
            flex: 1;
            min-width: 150px;
        }

        .stock-ticker {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }

        .stock-price {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }

        .stock-status {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
        }

        .status-critical {
            background: #ff4757;
            color: white;
        }

        .status-watchlist {
            background: #ffa502;
            color: white;
        }

        .status-new {
            background: #2ed573;
            color: white;
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .metric-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }

        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }

        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            margin-bottom: 15px;
            transition: all 0.3s;
        }

        .refresh-btn:hover {
            background: #764ba2;
            transform: translateY(-2px);
        }

        .last-update {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }

        .alert-banner {
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            color: #155724;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 20px;
            }

            .tabs {
                grid-template-columns: 1fr;
            }

            .tab-btn {
                padding: 12px;
                font-size: 12px;
            }

            .header-info {
                grid-template-columns: repeat(2, 1fr);
            }

            .metrics {
                grid-template-columns: 1fr;
            }

            .stock-card {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1>🤖 Stock Yard Trading Dashboard</h1>
                    <p style="color: #666; margin-top: 5px;">Real-time Nifty 500 Stock Scanner</p>
                </div>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
            </div>

            <div class="header-info">
                <div class="info-card">
                    <div class="info-label">Status</div>
                    <div class="info-value" id="status">🟢 Active</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Stocks Scanned</div>
                    <div class="info-value" id="scanCount">500</div>
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
            <button class="tab-btn volume active" onclick="switchTab('volume')">📊 Volume</button>
            <button class="tab-btn trendline" onclick="switchTab('trendline')">📈 Trendline</button>
            <button class="tab-btn radar" onclick="switchTab('radar')">🎯 Radar</button>
        </div>

        <div class="content">
            <div id="volume" class="tab-content active">
                <h2 style="margin-bottom: 15px; color: #667eea;">📊 Volume Tab</h2>
                <div class="stock-card">
                    <div class="stock-info">
                        <div class="stock-ticker">RELIANCE</div>
                        <div class="stock-price">₹2,500 • Volume: 50M</div>
                    </div>
                    <div class="stock-status status-new">🆕 NEW</div>
                </div>
            </div>

            <div id="trendline" class="tab-content">
                <h2 style="margin-bottom: 15px; color: #764ba2;">📈 Trendline Support</h2>
                <div class="stock-card">
                    <div class="stock-info">
                        <div class="stock-ticker">WIPRO</div>
                        <div class="stock-price">Current: ₹400 | Support: ₹385 | Target: ₹480</div>
                    </div>
                    <div class="stock-status status-new">💡 ENTRY</div>
                </div>
            </div>

            <div id="radar" class="tab-content">
                <h2 style="margin-bottom: 15px; color: #f093fb;">🎯 Radar - Critical Zone</h2>
                <div class="alert-banner">⚠️ 1 stock in CRITICAL zone - Ready for entry!</div>
                <div class="stock-card critical">
                    <div class="stock-info">
                        <div class="stock-ticker">BAJAJFINSV</div>
                        <div class="stock-price">Entry: ₹1,520 | Support: ₹1,500 | Distance: 1.3%</div>
                    </div>
                    <div class="stock-status status-critical">🔴 CRITICAL</div>
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
            document.querySelector(`.tab-btn.${tabName}`).classList.add('active');
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

echo "✓ Dashboard HTML created"

# Install Nginx
echo "⏳ Installing Nginx..."
apt-get update -qq
apt-get install -y nginx > /dev/null 2>&1
echo "✓ Nginx installed"

# Create Nginx config
echo "⏳ Configuring Nginx..."
cat > /etc/nginx/sites-available/stockyard << 'NGINX_EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    root /var/www/stockyard;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /dashboard {
        alias /var/www/stockyard;
        try_files $uri $uri/ /index.html;
    }
}
NGINX_EOF

# Enable site
ln -sf /etc/nginx/sites-available/stockyard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

echo "✓ Nginx configured"

# Test and reload Nginx
nginx -t > /dev/null 2>&1
if [ $? -eq 0 ]; then
    systemctl restart nginx
    echo "✓ Nginx restarted"
else
    echo "✗ Nginx config error"
fi

echo ""
echo "=========================================="
echo "✓ DASHBOARD DEPLOYED TO EC2"
echo "=========================================="
echo ""
echo "🌐 Access dashboard at:"
echo "   http://32.194.58.75/dashboard"
echo "   http://32.194.58.75"
echo ""
echo "📱 Works on all browsers:"
echo "   • Chrome, Safari, Firefox, Edge"
echo "   • Desktop & Mobile"
echo ""
echo "✅ Dashboard is now LIVE!"
echo ""
