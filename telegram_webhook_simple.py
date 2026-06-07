#!/usr/bin/env python3
"""
Simple Telegram Webhook for Trade Confirmation
- Receives button clicks from Telegram
- Calls angel_trade.py to execute
- Sends confirmation via Telegram
"""

import os
import json
import requests
import subprocess
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8901309420')

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
    except:
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
    except:
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
            
            print(f"🔘 Callback received: {callback_data}")
            
            # Parse callback data: confirm_trade:TICKER:PRICE:TARGET:SL
            parts = callback_data.split(':')
            
            if len(parts) >= 5 and parts[0] == 'confirm_trade':
                ticker = parts[1]
                entry_price = float(parts[2])
                target_price = float(parts[3])
                stoploss_price = float(parts[4])
                
                print(f"📊 Executing trade: {ticker} @ ₹{entry_price}")
                
                # Call angel_trade.py to execute
                try:
                    result = subprocess.run([
                        'python', 'angel_trade.py',
                        ticker,
                        str(entry_price),
                        str(target_price),
                        str(stoploss_price),
                        'Telegram'
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        print(f"✅ Trade executed successfully")
                        answer_callback(query_id, f"✅ Trade executed for {ticker}!")
                        return jsonify({'ok': True}), 200
                    else:
                        print(f"❌ Trade failed: {result.stderr}")
                        answer_callback(query_id, f"❌ Trade failed for {ticker}")
                        return jsonify({'ok': True}), 200
                        
                except subprocess.TimeoutExpired:
                    print("⏱️ Trade execution timeout")
                    answer_callback(query_id, "⏱️ Execution timeout")
                    return jsonify({'ok': True}), 200
                except Exception as e:
                    print(f"❌ Execution error: {e}")
                    answer_callback(query_id, f"❌ Error: {str(e)}")
                    return jsonify({'ok': True}), 200
            
            return jsonify({'ok': True}), 200
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    print("="*60)
    print("🚀 TELEGRAM WEBHOOK SERVER STARTING")
    print("="*60)
    print(f"Listening for Telegram callbacks at /webhook/telegram")
    print(f"Running on 0.0.0.0:5000")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
