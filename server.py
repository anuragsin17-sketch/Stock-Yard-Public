import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/place-trade', methods=['POST'])
def webhook():
    # Verify an optional secret token to ensure only your UI can trigger trades
    auth_token = request.headers.get('X-Trade-Secret')
    if auth_token != os.environ.get('WEBHOOK_SECRET_KEY'):
        return jsonify({"error": "Unauthorized"}), 401
        
    payload = request.json or {}
    client_payload = payload.get('client_payload', {})
    
    # Map the incoming data to environment variables for angel_trade.py
    os.environ['TRADE_SYMBOL'] = str(client_payload.get('symbol', ''))
    os.environ['TRADE_ACTION'] = str(client_payload.get('action', 'BUY'))
    os.environ['TRADE_PRICE'] = str(client_payload.get('price', '0'))
    os.environ['TRADE_QUANTITY'] = str(client_payload.get('quantity', '0'))
    
    try:
        # Run your working trading script
        result = subprocess.run(['python', 'angel_trade.py'], capture_output=True, text=True)
        return jsonify({"status": "Executed", "log": result.stdout}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
