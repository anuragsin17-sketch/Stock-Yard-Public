import json
import pandas as pd
import os
import requests
from datetime import datetime
from geometric_engine import MacroInstitutionalEngine

def send_telegram_alert(message: str) -> None:
    """Send Telegram notification for critical trendline alerts"""
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_bot_token or not telegram_chat_id:
        print("⚠️ Telegram credentials not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully")
        else:
            print(f"⚠️ Failed to send Telegram alert: {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending Telegram alert: {e}")

def synchronize_production_database():
    # Load your pattern engine parameters
    # ₹50,000 capital slots, 8% stop-loss threshold, ±2% touch tolerance
    engine = MacroInstitutionalEngine(position_size=50000.0, sl_pct=8.0, touch_tolerance=2.0)
    
    print("Connecting to NSE network to ingest active Nifty 500 components...")
    try:
        # Load Nifty 500 from local CSV
        df = pd.read_csv('ind_nifty500list.csv')
        tickers = [str(t).strip() + ".NS" for t in df['Symbol'].tolist() if str(t).strip()]
    print(f"Loaded {len(tickers)} tickers from Nifty 500 list")
    except Exception as e:
        print("Direct fetch failed, compiling core watchlist fallback sequence.")
        tickers = ["BHEL.NS", "CDSL.NS", "SBIN.NS", "AXISBANK.NS", "TATACONSUM.NS", "HINDALCO.NS", "INFY.NS", "GAIL.NS", "TECHM.NS", "BPCL.NS"]
        
    compiled_screen_data = []
    critical_alerts = []
    print(f"📋 Running multi-level structural matrix over {len(tickers)} assets...")
    
    for count, stock in enumerate(tickers, 1):
        data = engine.process_ticker_geometry(stock)
        if data:
            compiled_screen_data.append(data)
            print(f"   [+] Pattern Captured: {data['ticker']} | Zone: {data['patternZone']} | Dist: {data['distanceRemaining']}%")
            
            # Send Telegram alert for critical touches
            if data["notificationTrigger"]:
                alert_msg = f"TRENDLINE CRITICAL ENTRY\n\n" \
                           f"Stock: {data['ticker']}\n" \
                           f"Current: Rs{data['currentPrice']:,.2f}\n" \
                           f"Trigger: Rs{data['triggerPrice']:,.2f}\n" \
                           f"Distance: {data['distanceRemaining']:.2f}%\n" \
                           f"Zone: {data['patternZone']}\n" \
                           f"Target: Rs{data['positionSizing']['pivotTargetExit']:,.2f}\n" \
                           f"Stop Loss: Rs{data['positionSizing']['strictStopLoss']:,.2f}\n\n" \
                           f"Trendline scanner alert"
                
                print(f"   CRITICAL ALERT: {data['ticker']} at trendline trigger!")
                send_telegram_alert(alert_msg)
                critical_alerts.append(data['ticker'])

    # Write out the clean JSON data payload for your separated HTML screen loader
    with open("trendline_screen.json", "w") as json_file:
        json.dump(compiled_screen_data, json_file, indent=4)
        
    print(f"\n==================================================================")
    print(f"SUCCESS: trendline_screen.json updated with {len(compiled_screen_data)} matched rows.")
    if critical_alerts:
        print(f"CRITICAL ALERTS sent for: {', '.join(critical_alerts)}")
    print(f"==================================================================")

if __name__ == "__main__":
    synchronize_production_database()
