#!/usr/bin/env python3
"""
Local Trade Testing Server
Run on http://localhost:8080 to test Angel One order placement
"""

import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

class TradeTestHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Serve the test UI"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Angel One Trade Tester - Local</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #38bdf8; margin-bottom: 10px; }
        .form-section { background-color: #1e293b; padding: 25px; border-radius: 8px; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #94a3b8; font-size: 14px; margin-bottom: 8px; font-weight: 600; }
        input, select { width: 100%; padding: 12px; background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #f8fafc; font-size: 14px; }
        input:focus, select:focus { outline: none; border-color: #38bdf8; }
        .btn { background-color: #0369a1; color: #ffffff; border: none; padding: 14px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: 600; width: 100%; margin-top: 10px; }
        .btn:hover { background-color: #0284c7; }
        .btn:disabled { background-color: #334155; cursor: not-allowed; }
        .result { padding: 15px; border-radius: 6px; margin-top: 20px; display: none; }
        .success { background-color: #065f46; color: #d1fae5; display: block; }
        .error { background-color: #7f1d1d; color: #fecaca; display: block; }
        .info { background-color: #1e3a8a; color: #bfdbfe; display: block; }
        pre { background-color: #0f172a; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 12px; margin-top: 10px; }
        .warning { background-color: #78350f; color: #fef3c7; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
        .credentials-note { background-color: #1e3a8a; color: #bfdbfe; padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 13px; }
    </style>
</head>
<body>

<div class="container">
    <h1>🚀 Angel One Trade Tester</h1>
    <p style="color: #94a3b8; margin-bottom: 20px;">Test order placement locally on port 8080</p>

    <div class="credentials-note">
        ℹ️ <strong>Note:</strong> Set your Angel One credentials as environment variables before testing:
        <code>ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET</code>
    </div>

    <div class="form-section">
        <h2 style="color: #38bdf8; font-size: 18px; margin-bottom: 20px;">Order Details (4 Parameters Only)</h2>
        
        <form id="trade-form">
            <div class="form-group">
                <label for="symbol">1. Stock Symbol *</label>
                <input type="text" id="symbol" name="symbol" placeholder="e.g., JKCEMENT" required>
            </div>

            <div class="form-group">
                <label for="action">2. Action *</label>
                <select id="action" name="action" required>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                </select>
            </div>

            <div class="form-group">
                <label for="price">3. Entry Price (₹) *</label>
                <input type="number" id="price" name="price" step="0.01" placeholder="e.g., 4250.50" required>
            </div>

            <div class="form-group">
                <label for="quantity">4. Quantity *</label>
                <input type="number" id="quantity" name="quantity" min="1" placeholder="e.g., 10" required>
            </div>

            <button type="submit" class="btn" id="submit-btn">Place Test Order</button>
        </form>
    </div>

    <div id="result-container"></div>
</div>

<script>
    document.getElementById('trade-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submit-btn');
        const resultContainer = document.getElementById('result-container');
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Placing Order...';
        
        const formData = {
            symbol: document.getElementById('symbol').value.toUpperCase(),
            action: document.getElementById('action').value,
            price: document.getElementById('price').value,
            quantity: document.getElementById('quantity').value
        };
        
        try {
            const response = await fetch('/place_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                resultContainer.innerHTML = `
                    <div class="result success">
                        <strong>✅ Order Test Completed!</strong><br><br>
                        ${result.message}
                        <pre>${result.output}</pre>
                    </div>
                `;
            } else {
                resultContainer.innerHTML = `
                    <div class="result error">
                        <strong>❌ Order Test Failed</strong><br><br>
                        ${result.message}
                        <pre>${result.output}</pre>
                    </div>
                `;
            }
        } catch (error) {
            resultContainer.innerHTML = `
                <div class="result error">
                    <strong>❌ Request Failed</strong><br><br>
                    ${error.message}
                </div>
            `;
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Place Test Order';
        }
    });
</script>

</body>
</html>
            """
            
            self.wfile.write(html.encode())
        
        elif self.path == '/trendline_screen.html':
            # Serve the trendline screen
            try:
                with open('trendline_screen.html', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content.encode())
            except FileNotFoundError:
                self.send_error(404, 'File not found')
        
        elif self.path == '/trendline_screen.json':
            # Serve the JSON data
            try:
                with open('trendline_screen.json', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(content.encode())
            except FileNotFoundError:
                self.send_error(404, 'File not found')
        
        else:
            self.send_error(404, 'File not found')
    
    def do_POST(self):
        """Handle order placement"""
        if self.path == '/place_order':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            # Set environment variables (ONLY 4 parameters)
            os.environ['TRADE_SYMBOL'] = data['symbol']
            os.environ['TRADE_ACTION'] = data['action']
            os.environ['TRADE_PRICE'] = str(data['price'])
            os.environ['TRADE_QUANTITY'] = str(data['quantity'])
            
            # Run angel_trade.py
            try:
                result = subprocess.run(
                    ['python', 'angel_trade.py'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                response = {
                    'success': result.returncode == 0,
                    'message': 'Order executed successfully' if result.returncode == 0 else 'Order execution failed',
                    'output': result.stdout + '\n' + result.stderr
                }
            except subprocess.TimeoutExpired:
                response = {
                    'success': False,
                    'message': 'Order execution timed out',
                    'output': 'Process took longer than 30 seconds'
                }
            except Exception as e:
                response = {
                    'success': False,
                    'message': f'Error executing order: {str(e)}',
                    'output': str(e)
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404, 'Endpoint not found')
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, TradeTestHandler)
    print(f"")
    print(f"🚀 Local Trade Testing Server Started!")
    print(f"")
    print(f"📍 Server running at: http://localhost:{port}")
    print(f"")
    print(f"Available endpoints:")
    print(f"  • http://localhost:{port}/                  - Angel One Trade Tester")
    print(f"  • http://localhost:{port}/trendline_screen.html - Trendline Scanner Dashboard")
    print(f"")
    print(f"Press Ctrl+C to stop the server")
    print(f"")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Server stopped")
        httpd.server_close()


if __name__ == '__main__':
    run_server(8080)
