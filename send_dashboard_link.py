#!/usr/bin/env python3
"""
Send dashboard link via Telegram
Sends the dashboard URL to your Telegram chat
"""

import json
import requests

def send_telegram_message(config_path='d:\\Stock Yard\\aws_config.json'):
    """Send dashboard link via Telegram"""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False
    
    telegram_token = config.get('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = config.get('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not telegram_chat_id:
        print("✗ Telegram token or chat ID not found in config")
        return False
    
    # Dashboard URL
    dashboard_url = "http://32.194.58.75"
    
    print("\n" + "="*60)
    print("SENDING DASHBOARD LINK VIA TELEGRAM")
    print("="*60 + "\n")
    
    # Create message
    message = f"""
🤖 Stock Yard Trading Dashboard

Your real-time dashboard is now live!

📊 Access here: {dashboard_url}

Features:
✅ Volume Tab - High activity stocks
✅ Trendline Support - Entry opportunities  
✅ Radar (Critical) - Critical signals

⏱️ Auto-refreshes every 5 minutes
📱 Works on all browsers & mobile

Share with your team!
"""
    
    try:
        # Send via Telegram Bot API
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        
        params = {
            'chat_id': telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("✓ Message sent successfully!")
            print(f"  Chat ID: {telegram_chat_id}")
            print(f"  Dashboard: {dashboard_url}\n")
            return True
        else:
            print(f"✗ Failed to send message: {response.status_code}")
            print(f"  Response: {response.text}\n")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Timeout sending message")
        return False
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False


def send_critical_alert(ticker, price, distance, config_path='d:\\Stock Yard\\aws_config.json'):
    """Send critical stock alert via Telegram"""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False
    
    telegram_token = config.get('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = config.get('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not telegram_chat_id:
        return False
    
    message = f"""
🔴 CRITICAL ENTRY SIGNAL

Stock: {ticker}
Current Price: {price}
Distance: {distance}%

⚡ Ready to enter!

📊 View full details: http://32.194.58.75
"""
    
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        
        params = {
            'chat_id': telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, params=params, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"⚠️  Alert not sent: {e}")
        return False


if __name__ == '__main__':
    send_telegram_message()
