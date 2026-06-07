#!/bin/bash
# This script creates a systemd service to run the Telegram test on EC2

# SSH into instance and run these commands:
# ssh -i your-key.pem ubuntu@32.194.58.75

# Once connected, run:

# 1. Create test script
cat > /home/ubuntu/test_telegram.py << 'EOF'
#!/usr/bin/env python3
import json
import requests
import time
from pathlib import Path

def load_telegram_config():
    config_path = Path('/home/ubuntu/stock_yard_config/bot_config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except:
        return {'TELEGRAM_BOT_TOKEN': '', 'TELEGRAM_CHAT_ID': ''}

def send_telegram_message(bot_token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

# Load config
config = load_telegram_config()
bot_token = config.get('TELEGRAM_BOT_TOKEN', '')
chat_id = config.get('TELEGRAM_CHAT_ID', '')

print("\n🤖 Stock Yard Bot - Telegram Test\n")

if not bot_token or not chat_id:
    print("✗ Telegram credentials not configured!")
    print(f"  Bot Token: {bot_token if bot_token else 'NOT SET'}")
    print(f"  Chat ID: {chat_id if chat_id else 'NOT SET'}")
else:
    print("✓ Sending test messages...\n")
    
    messages = [
        "🤖 <b>Stock Yard Bot Online!</b>\nTelegram notifications working ✅",
        "📊 <b>System Ready</b>\nBot is monitoring Nifty 500 stocks",
        "✅ <b>All Systems GO!</b>\nBot is ready for live trading 🚀"
    ]
    
    for i, msg in enumerate(messages, 1):
        if send_telegram_message(bot_token, chat_id, msg):
            print(f"✓ Message {i} sent")
            time.sleep(1)
        else:
            print(f"✗ Message {i} failed")
    
    print("\n✓ Test complete! Check your Telegram.\n")
EOF

chmod +x /home/ubuntu/test_telegram.py

# 2. Run the test
python3 /home/ubuntu/test_telegram.py

# That's it! You should see 3 test messages in Telegram now.
