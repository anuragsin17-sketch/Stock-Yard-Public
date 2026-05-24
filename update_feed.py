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
        print("Telegram credentials not configured")
        return

    try:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully")
        else:
            print(f"Telegram failed: {response.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

def synchronize_production_database():
    engine = MacroInstitutionalEngine(position_size=50000.0, sl_pct=8.0, touch_tolerance=2.0)

    print("Connecting to NSE network...")

    # Load Nifty 500 tickers - FIX: print was outside try block before
    try:
        df = pd.read_csv('ind_nifty500list.csv')
        tickers = [str(t).strip() + ".NS" for t in df['Symbol'].tolist() if str(t).strip()]
        print(f"Loaded {len(tickers)} tickers from Nifty 500 list")
    except Exception as e:
        print(f"CSV load failed: {e}, using fallback list")
        tickers = ["SBIN.NS", "AXISBANK.NS", "INFY.NS", "RELIANCE.NS", "HDFCBANK.NS",
                   "TCS.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "LT.NS", "TITAN.NS"]

    compiled_screen_data = []
    critical_alerts = []
    watchlist_alerts = []

    print(f"Scanning {len(tickers)} stocks for trendline signals...")

    for count, stock in enumerate(tickers, 1):
        try:
            data = engine.process_ticker_geometry(stock)
            if data:
                # Build record matching trendline_screen.html format
                record = {
                    "ticker": data["ticker"],
                    "currentPrice": data["currentSignal"]["currentPrice"],
                    "triggerPrice": data["currentSignal"]["triggerPrice"],
                    "distanceRemaining": data["currentSignal"]["distanceRemaining"],
                    "fibLevelMatch": data["currentSignal"].get("fibLevelMatch", "N/A"),
                    "patternZone": data["currentSignal"].get("confluenceNote", "Trendline Support"),
                    "notificationTrigger": data["currentSignal"]["notificationTrigger"],
                    "positionSizing": {
                        "sharesToBuy": data["positionSizing"]["sharesToBuy"],
                        "strictStopLoss": data["positionSizing"]["dynamicStopLoss"],
                        "pivotTargetExit": data["positionSizing"]["targetExit"],
                        "allocatedAmount": 50000.0
                    },
                    "wickTouches": data["trendlineDetails"]["wickTouches"],
                    "timeframe": data["trendlineDetails"].get("timeframe", "monthly"),
                    "confluenceScore": data["currentSignal"]["confluenceScore"]
                }

                compiled_screen_data.append(record)
                print(f"   [+] {data['ticker']:12} | Rs{record['currentPrice']:8.2f} | Trigger: Rs{record['triggerPrice']:8.2f} | Dist: {record['distanceRemaining']:.2f}%")

                # Track critical and watchlist (no individual alerts)
                if data["currentSignal"]["notificationTrigger"]:
                    critical_alerts.append(data['ticker'])
                elif record['distanceRemaining'] <= 2.0:
                    watchlist_alerts.append(data['ticker'])

        except Exception as e:
            print(f"   Error {stock}: {e}")
            continue

    # Sort by distance (closest first)
    compiled_screen_data.sort(key=lambda x: x['distanceRemaining'])

    # Write JSON for HTML dashboard
    with open("trendline_screen.json", "w") as f:
        json.dump(compiled_screen_data, f, indent=4)

    print(f"\n==================================================================")
    print(f"SUCCESS: trendline_screen.json updated with {len(compiled_screen_data)} signals")
    print(f"Critical alerts: {len(critical_alerts)} - {', '.join(critical_alerts) if critical_alerts else 'None'}")
    print(f"Watchlist: {len(watchlist_alerts)} - {', '.join(watchlist_alerts[:10]) if watchlist_alerts else 'None'}")
    print(f"==================================================================")

    # Base URL for deep links
    base_url = "https://anuragsin17-sketch.github.io/Stock-Yard-Public"

    # Send individual critical alerts with deep link (tap to confirm trade)
    for record in compiled_screen_data:
        if record['notificationTrigger']:  # +-1% critical
            ticker = record['ticker']
            price = record['triggerPrice']
            stop = record['positionSizing']['strictStopLoss']
            target = record['positionSizing']['pivotTargetExit']
            qty = record['positionSizing']['sharesToBuy']
            dist = record['distanceRemaining']

            # Deep link - opens dashboard and auto-triggers confirm dialog
            confirm_url = (
                f"{base_url}/?confirm={ticker}"
                f"&price={price}"
                f"&qty={qty}"
                f"&stop={stop}"
                f"&target={target}"
                f"&source=Trendline"
            )

            alert = (
                f"🎯 *CRITICAL TRENDLINE ENTRY*\n\n"
                f"*Stock:* {ticker}\n"
                f"*Current:* Rs{record['currentPrice']:,.2f}\n"
                f"*Trigger:* Rs{price:,.2f} ({dist:.2f}% away)\n"
                f"*Stop Loss:* Rs{stop:,.2f} (Monthly Close)\n"
                f"*Target:* Rs{target:,.2f} (+20%)\n"
                f"*Qty:* {qty} shares\n\n"
                f"Tap to confirm trade:\n{confirm_url}"
            )
            send_telegram_alert(alert)
            print(f"   Critical alert sent for {ticker} with deep link")

    # Send summary Telegram
    if compiled_screen_data:
        summary = (
            f"📊 *Trendline Scanner Summary*\n\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n"
            f"📈 Total signals: {len(compiled_screen_data)}\n"
            f"🎯 Critical (+-1%): {len(critical_alerts)}\n"
            f"👀 Watchlist (+-2%): {len(watchlist_alerts)}\n"
        )
        if critical_alerts:
            summary += f"\n*Critical stocks:* {', '.join(critical_alerts)}"
        if watchlist_alerts:
            summary += f"\n*Watchlist:* {', '.join(watchlist_alerts[:5])}"
        summary += f"\n\n📱 *View Full Report:*\nhttps://anuragsin17-sketch.github.io/Stock-Yard-Public/"
        send_telegram_alert(summary)

if __name__ == "__main__":
    synchronize_production_database()
