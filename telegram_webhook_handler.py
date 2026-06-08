#!/usr/bin/env python3
"""
Telegram Webhook Handler for Stock Yard
Receives callback queries from Telegram buttons and places orders
"""

import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8901309420')
API_URL = "http://localhost:5000"  # Call local API on same EC2

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'telegram-webhook'}), 200

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Receive webhook from Telegram"""
    try:
        update = request.json
        logger.info(f"Received update: {json.dumps(update, indent=2)}")
        
        # Handle callback query (button clicks)
        if 'callback_query' in update:
            callback = update['callback_query']
            callback_id = callback.get('id')
            callback_data = callback.get('data')
            user_id = callback.get('from', {}).get('id')
            
            logger.info(f"Callback received: {callback_data} from user {user_id}")
            
            if callback_data == 'cancel_trade':
                # User cancelled
                answer_callback(callback_id, "Trade cancelled ❌")
                send_message("Trade cancelled by user")
                return jsonify({'ok': True}), 200
            
            # Extract token from callback_data (it's the token itself)
            token = callback_data
            
            # Verify token and get trade details
            token_file = '/home/ubuntu/active_trade_tokens.json'
            if not os.path.exists(token_file):
                answer_callback(callback_id, "Token file not found ❌")
                return jsonify({'ok': False}), 400
            
            try:
                with open(token_file) as f:
                    tokens = json.load(f)
            except Exception as e:
                logger.error(f"Error reading token file: {e}")
                answer_callback(callback_id, "Error reading tokens ❌")
                return jsonify({'ok': False}), 400
            
            if token not in tokens:
                logger.warning(f"Invalid token: {token[:20]}...")
                answer_callback(callback_id, "Invalid token ❌")
                return jsonify({'ok': False}), 401
            
            token_data = tokens[token]
            ticker = token_data.get('ticker')
            entry_price = token_data.get('currentPrice')
            target = token_data.get('targetExit')
            stop_loss = token_data.get('stopLoss')
            qty = token_data.get('sharesToBuy', 1)
            
            logger.info(f"Placing order for {ticker}")
            
            # Place order via API
            try:
                response = requests.post(
                    f"{API_URL}/api/place-order",
                    json={
                        "token": token,
                        "symbol": ticker,
                        "quantity": qty,
                        "entry_price": entry_price,
                        "target_price": target,
                        "stop_loss": stop_loss
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        order_id = result.get('order_id')
                        logger.info(f"Order placed: {order_id}")
                        
                        # Answer callback with success
                        answer_callback(callback_id, "Order placed! ✅")
                        
                        # Send confirmation message
                        msg = f"""✅ ORDER EXECUTED

Order ID: <b>{order_id}</b>
Stock: <b>{ticker}</b>
Quantity: {qty}
Entry: ₹{entry_price:,.2f}
Target: ₹{target:,.2f}
Stop Loss: ₹{stop_loss:,.2f}

Position is now LIVE! 🎯"""
                        
                        send_message(msg, parse_mode='HTML')
                        return jsonify({'ok': True}), 200
                    else:
                        error = result.get('error', 'Unknown error')
                        logger.error(f"Order failed: {error}")
                        answer_callback(callback_id, f"Order failed: {error}")
                        return jsonify({'ok': False}), 400
                else:
                    logger.error(f"API error: {response.status_code}")
                    answer_callback(callback_id, "API error ❌")
                    return jsonify({'ok': False}), 400
                    
            except requests.exceptions.Timeout:
                logger.error("API timeout")
                answer_callback(callback_id, "Order timeout ⏱️")
                return jsonify({'ok': False}), 408
            except Exception as e:
                logger.error(f"Order error: {e}")
                answer_callback(callback_id, "Order error ❌")
                return jsonify({'ok': False}), 500
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

def answer_callback(callback_id, text):
    """Send callback answer to Telegram (shows alert)"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_id,
            'text': text,
            'show_alert': False
        }
        requests.post(url, json=payload, timeout=10)
        logger.info(f"Callback answered: {text}")
    except Exception as e:
        logger.error(f"Error answering callback: {e}")

def send_message(text, parse_mode='HTML'):
    """Send message to Telegram chat"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Message sent to Telegram")
        else:
            logger.error(f"Failed to send message: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

@app.route('/webhook/register', methods=['POST'])
def register_webhook():
    """Register webhook URL with Telegram"""
    try:
        webhook_url = request.json.get('webhook_url')
        if not webhook_url:
            return jsonify({'error': 'webhook_url required'}), 400
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        payload = {
            'url': webhook_url,
            'allowed_updates': ['callback_query']
        }
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"Webhook registered: {webhook_url}")
            return jsonify({'ok': True, 'message': 'Webhook registered'}), 200
        else:
            logger.error(f"Webhook registration failed: {result}")
            return jsonify({'ok': False, 'error': result.get('description')}), 400
            
    except Exception as e:
        logger.error(f"Webhook registration error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/webhook/info', methods=['GET'])
def webhook_info():
    """Get current webhook info"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        info = response.json()
        
        if info.get('ok'):
            return jsonify(info.get('result')), 200
        else:
            return jsonify({'error': info.get('description')}), 400
            
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Telegram Webhook Handler")
    logger.info(f"Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
