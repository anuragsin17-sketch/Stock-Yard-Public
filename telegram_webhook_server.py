#!/usr/bin/env python3
"""
Telegram Webhook Server for handling callback queries
- Runs on EC2
- Listens for button clicks from Telegram alerts
- Updates position sizing and executes trades
- Sends confirmations back to Telegram
"""

import os
import json
from flask import Flask, request, jsonify
from telegram_trade_bot import process_callback_query, TelegramTradeBot

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', 'stockyard-secret-key')


@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    Handle incoming Telegram updates
    Called when user clicks a button in Telegram alert
    """
    try:
        update = request.get_json()
        
        if not update:
            return jsonify({'ok': True}), 200
        
        # Handle callback query (button clicks)
        if 'callback_query' in update:
            callback_query = update['callback_query']
            query_id = callback_query.get('id')
            callback_data = callback_query.get('data', '')
            message = callback_query.get('message', {})
            message_id = message.get('message_id')
            
            print(f"🔘 Callback received: {callback_data}")
            
            # Process the callback
            result = process_callback_query(query_id, callback_data, message_id)
            
            return jsonify({'ok': result}), 200
        
        # Handle regular messages
        elif 'message' in update:
            message = update['message']
            text = message.get('text', '')
            chat_id = message.get('chat', {}).get('id')
            
            print(f"💬 Message received: {text}")
            
            # Echo back
            bot = TelegramTradeBot()
            bot.send_message(f"✅ Received: {text}")
            
            return jsonify({'ok': True}), 200
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'bot': 'active'}), 200


@app.route('/status', methods=['GET'])
def status():
    """Get bot status"""
    return jsonify({
        'status': 'running',
        'telegram_configured': bool(TELEGRAM_BOT_TOKEN),
        'webhook_url': '/webhook/telegram',
        'timestamp': str(__import__('datetime').datetime.now().isoformat())
    }), 200


if __name__ == '__main__':
    print("🚀 Telegram Webhook Server Starting...")
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:10]}..." if TELEGRAM_BOT_TOKEN else "❌ No token")
    print(f"Webhook URL: /webhook/telegram")
    print(f"Health Check: /health")
    print(f"Status: /status")
    
    # Run on 0.0.0.0 so EC2 can access it
    app.run(host='0.0.0.0', port=5000, debug=False)
