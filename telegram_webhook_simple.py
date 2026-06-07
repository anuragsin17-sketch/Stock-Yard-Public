#!/usr/bin/env python3
"""
Telegram Webhook Server for Trade Confirmation
- Receives button clicks from Telegram
- Calls angel_trade.py to execute trades
- Sends confirmation via Telegram
- Production-ready with Gunicorn
"""

import os
import json
import requests
import subprocess
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://32.194.58.75:8443/webhook/telegram')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
else:
    logger.info(f"✅ Telegram configured for chat {TELEGRAM_CHAT_ID[:10]}...")

def send_telegram(message: str) -> bool:
    """Send Telegram message"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ send_telegram error: {e}")
        return False

def answer_callback(query_id: str, text: str) -> bool:
    """Answer callback query"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={
                'callback_query_id': query_id,
                'text': text,
                'show_alert': True
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ answer_callback error: {e}")
        return False

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Handle Telegram callback queries"""
    try:
        update = request.get_json()
        
        if 'callback_query' in update:
            callback_query = update['callback_query']
            query_id = callback_query.get('id')
            callback_data = callback_query.get('data', '')
            user_id = callback_query.get('from', {}).get('id')
            
            logger.info(f"🔘 Callback received: {callback_data} from user {user_id}")
            
            # Parse callback data: confirm_trade:TICKER:PRICE:TARGET:SL:QTY
            parts = callback_data.split(':')
            
            if len(parts) >= 5 and parts[0] == 'confirm_trade':
                ticker = parts[1]
                entry_price = float(parts[2])
                target_price = float(parts[3])
                stoploss_price = float(parts[4])
                quantity = int(parts[5]) if len(parts) > 5 else 10
                
                logger.info(f"📊 Executing trade: {ticker} @ ₹{entry_price} qty={quantity}")
                
                # Call angel_trade.py to execute
                try:
                    result = subprocess.run([
                        'python3', 'angel_trade.py',
                        ticker,
                        str(entry_price),
                        str(target_price),
                        str(stoploss_price),
                        'Telegram'
                    ], capture_output=True, text=True, timeout=30, cwd='/home/ubuntu')
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Trade executed for {ticker}")
                        answer_callback(query_id, f"✅ Trade confirmed!\n{ticker} @ ₹{entry_price}")
                        
                        # Send confirmation message
                        conf_msg = (
                            f"✅ *TRADE EXECUTED*\n\n"
                            f"📈 {ticker}\n"
                            f"💹 Entry: ₹{entry_price:,.0f}\n"
                            f"📊 Qty: {quantity}\n"
                            f"🎯 Target: ₹{target_price:,.0f}\n"
                            f"🛑 SL: ₹{stoploss_price:,.0f}\n"
                            f"⏰ {datetime.now().strftime('%H:%M IST')}"
                        )
                        send_telegram(conf_msg)
                        return jsonify({'ok': True}), 200
                    else:
                        logger.error(f"❌ Trade execution failed: {result.stderr}")
                        answer_callback(query_id, f"❌ Failed: {result.stderr[:100]}")
                        return jsonify({'ok': True}), 200
                        
                except subprocess.TimeoutExpired:
                    logger.error("⏱️ Trade execution timeout")
                    answer_callback(query_id, "⏱️ Execution timeout (30s)")
                    return jsonify({'ok': True}), 200
                except Exception as e:
                    logger.error(f"❌ Execution error: {e}")
                    answer_callback(query_id, f"❌ Error: {str(e)[:50]}")
                    return jsonify({'ok': True}), 200
            
            elif callback_data.startswith('skip_trade:'):
                ticker = callback_data.split(':')[1]
                logger.info(f"⏭️ Skipped trade: {ticker}")
                answer_callback(query_id, f"⏭️ Skipped {ticker}")
                return jsonify({'ok': True}), 200
            
            return jsonify({'ok': True}), 200
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/register-webhook', methods=['POST'])
def register_webhook():
    """Register this webhook URL with Telegram"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={
                'url': WEBHOOK_URL,
                'allowed_updates': ['callback_query'],
                'max_connections': 10
            },
            timeout=10
        )
        
        result = response.json()
        if result.get('ok'):
            logger.info(f"✅ Webhook registered: {WEBHOOK_URL}")
            return jsonify({'ok': True, 'message': 'Webhook registered'}), 200
        else:
            logger.error(f"❌ Webhook registration failed: {result}")
            return jsonify({'ok': False, 'error': result.get('description')}), 400
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🚀 TELEGRAM WEBHOOK SERVER STARTING")
    logger.info("="*60)
    logger.info(f"Listening for Telegram callbacks at {WEBHOOK_URL}")
    logger.info("Running on 0.0.0.0:8443")
    logger.info("="*60)
    
    # Note: In production, use Gunicorn instead of Flask dev server
    # gunicorn --certfile=/etc/ssl/certs/telegram.crt --keyfile=/etc/ssl/private/telegram.key --bind 0.0.0.0:8443 telegram_webhook_simple:app
    app.run(host='0.0.0.0', port=8443, debug=False, ssl_context='adhoc')
