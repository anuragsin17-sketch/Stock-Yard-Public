# Fix SSH key permissions and deploy to EC2 - RUN THIS ONCE

$EC2_IP = "32.194.58.75"
$EC2_USER = "ubuntu"

# Find SSH key in common locations
$possibleKeyPaths = @(
    "$env:USERPROFILE\.ssh\stock-yard-key.pem",
    "$env:USERPROFILE\.ssh\id_rsa",
    "$env:USERPROFILE\.ssh\aws.pem",
    "C:\Users\$env:USERNAME\.ssh\stock-yard-key.pem",
    "C:\Users\$env:USERNAME\.ssh\id_rsa"
)

$keyPath = $null
foreach ($path in $possibleKeyPaths) {
    if (Test-Path $path) {
        $keyPath = $path
        Write-Host "✓ Found SSH key at: $keyPath" -ForegroundColor Green
        break
    }
}

if (-not $keyPath) {
    Write-Host "✗ SSH key not found in any expected location:" -ForegroundColor Red
    $possibleKeyPaths | ForEach-Object { Write-Host "  - $_" }
    
    Write-Host "`nPlease provide the path to your SSH key:" -ForegroundColor Yellow
    $keyPath = Read-Host "SSH key path"
    
    if (-not (Test-Path $keyPath)) {
        Write-Host "✗ File not found: $keyPath" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nUsing SSH key: $keyPath" -ForegroundColor Cyan

# Fix SSH key permissions (Windows SSH requirement)
Write-Host "`nFixing SSH key permissions..." -ForegroundColor Cyan
icacls $keyPath /inheritance:r | Out-Null
icacls $keyPath /grant:r "$env:USERNAME`:F" | Out-Null
Write-Host "✓ SSH key permissions fixed" -ForegroundColor Green

# Test SSH connection
Write-Host "`nTesting SSH connection..." -ForegroundColor Cyan
try {
    $testResult = ssh -i $keyPath -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" "echo OK" 2>&1
    if ($testResult -eq "OK") {
        Write-Host "✓ SSH connection successful" -ForegroundColor Green
    } else {
        Write-Host "⚠ SSH connection returned: $testResult" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ SSH test error: $_" -ForegroundColor Yellow
}

# Create deployment script
Write-Host "`nCreating deployment script..." -ForegroundColor Cyan

$deployScript = @'
#!/bin/bash
sudo systemctl stop angel-api 2>/dev/null || true
sleep 1

# Update the handler file
sudo tee /home/ubuntu/angel_order_handler.py > /dev/null << 'PYTHON_CODE'
#!/usr/bin/env python3
import os, sys, json, secrets, pyotp, logging
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)
app = Flask(__name__)

def load_credentials():
    creds = {
        'ANGEL_API_KEY': os.environ.get('ANGEL_API_KEY'),
        'ANGEL_CLIENT_ID': os.environ.get('ANGEL_CLIENT_ID'),
        'ANGEL_PASSWORD': os.environ.get('ANGEL_PASSWORD'),
        'ANGEL_TOTP_SECRET': os.environ.get('ANGEL_TOTP_SECRET'),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning(f"Missing: {', '.join(missing)}")
        return None
    return creds

def get_angel_session():
    creds = load_credentials()
    if not creds:
        logger.error("Credentials not configured")
        return None
    try:
        smart = SmartConnect(api_key=creds['ANGEL_API_KEY'])
        totp = pyotp.TOTP(creds['ANGEL_TOTP_SECRET']).now()
        session = smart.generateSession(creds['ANGEL_CLIENT_ID'], creds['ANGEL_PASSWORD'], totp)
        if not isinstance(session, dict) or not session.get('status'):
            logger.error("Session failed")
            return None
        logger.info("Angel One connected")
        return smart
    except Exception as e:
        logger.error(f"Session error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    creds = load_credentials()
    if creds:
        return jsonify({'status': 'ok', 'service': 'angel-api'}), 200
    return jsonify({'status': 'error', 'error': 'No credentials'}), 503

@app.route('/api/place-order', methods=['POST'])
def place_order():
    try:
        data = request.json
        symbol = data.get('symbol')
        quantity = int(data.get('quantity', 1))
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        
        logger.info(f"Order: {symbol} x{quantity} @ Rs{entry_price}")
        
        if not symbol:
            return jsonify({'success': False, 'error': 'No symbol'}), 400
        
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Angel connection failed'}), 401
        
        search_result = smart.searchScrip("NSE", symbol)
        if not search_result.get('data'):
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found'}), 404
        
        scrip_data = None
        for result in search_result['data']:
            if result.get('tradingsymbol') == symbol + '-EQ':
                scrip_data = result
                break
        if not scrip_data:
            scrip_data = search_result['data'][0]
        
        trading_symbol = scrip_data.get('tradingsymbol')
        symbol_token = scrip_data.get('symboltoken')
        
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": symbol_token,
            "transactiontype": "BUY",
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(int(entry_price)),
            "quantity": str(quantity),
            "squareoff": "0",
            "stoploss": "0",
            "trailingstoploss": "0"
        }
        
        logger.info(f"Placing order: {trading_symbol}")
        result = smart.placeOrder(order_params)
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', result.get('orderid'))
        else:
            logger.error(f"Order failed: {result}")
            return jsonify({'success': False, 'error': 'Order placement failed'}), 400
        
        logger.info(f"Order placed: {order_id}")
        
        order_record = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'placed_at': datetime.now().isoformat(),
            'status': 'PLACED'
        }
        
        orders_log = []
        if os.path.exists('angel_orders.json'):
            try:
                with open('angel_orders.json') as f:
                    orders_log = json.load(f)
                    if not isinstance(orders_log, list):
                        orders_log = []
            except:
                orders_log = []
        
        orders_log.append(order_record)
        with open('angel_orders.json', 'w') as f:
            json.dump(orders_log, f, indent=2)
        
        return jsonify({'success': True, 'order_id': order_id, 'symbol': symbol, 'quantity': quantity}), 200
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/order-status/<order_id>', methods=['GET'])
def order_status(order_id):
    try:
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Connection failed'}), 401
        
        orders = smart.orderBook()
        if not isinstance(orders, dict) or not orders.get('data'):
            return jsonify({'success': False, 'error': 'No orders'}), 404
        
        for order in orders['data']:
            if order.get('orderid') == order_id:
                return jsonify({'success': True, 'order': {
                    'order_id': order.get('orderid'),
                    'symbol': order.get('tradingsymbol'),
                    'status': order.get('status'),
                    'quantity': order.get('quantity'),
                    'filled': order.get('filledshares'),
                    'price': order.get('price')
                }}), 200
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    creds = load_credentials()
    if not creds:
        logger.error("FATAL: Credentials not set!")
        sys.exit(1)
    logger.info("Angel API starting on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
PYTHON_CODE

sudo systemctl restart angel-api
sleep 2
sudo systemctl status angel-api
echo ""
echo "✓ Deployment complete. Logs:"
sudo journalctl -u angel-api -n 10 --no-pager
'@

# Save deployment script
$deployScriptPath = "/tmp/deploy_$(Get-Random).sh"
Write-Host "`nRunning deployment on EC2..." -ForegroundColor Cyan

# Execute deployment via SSH
$result = ssh -i $keyPath -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" $deployScript 2>&1

Write-Host $result

# Test health endpoint
Write-Host "`nTesting health endpoint..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
try {
    $healthResponse = Invoke-WebRequest -Uri "http://${EC2_IP}:5000/health" -TimeoutSec 5 -ErrorAction Stop
    $healthData = $healthResponse.Content | ConvertFrom-Json
    Write-Host "✓ Service is running: $($healthData.status)" -ForegroundColor Green
} catch {
    Write-Host "⚠ Health check failed (service may still be starting): $_" -ForegroundColor Yellow
}

Write-Host "`n✓ Deployment complete!" -ForegroundColor Green
Write-Host "Next: Run python test_order_placement.py from your PC" -ForegroundColor Cyan
