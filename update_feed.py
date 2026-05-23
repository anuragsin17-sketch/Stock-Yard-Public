import json
import pandas as pd
from geometric_engine import MacroInstitutionalEngine

def synchronize_production_database():
    # Load your pattern engine parameters
    # ₹50,000 capital slots, 8% stop-loss threshold, 10% nearby filter buffer
    engine = MacroInstitutionalEngine(position_size=50000.0, sl_pct=8.0, watchlist_buffer=10.0)
    
    print("⏳ Connecting to NSE network to ingest active Nifty 500 components...")
    try:
        # Load Nifty 500 from local CSV
        df = pd.read_csv('ind_nifty500list.csv')
        tickers = [str(t).strip() + ".NS" for t in df['Symbol'].tolist() if str(t).strip()]
        print(f"✅ Loaded {len(tickers)} tickers from Nifty 500 list")
    except Exception as e:
        print("⚠️ Direct fetch failed, compiling core watchlist fallback sequence.")
        tickers = ["BHEL.NS", "CDSL.NS", "SBIN.NS", "AXISBANK.NS", "TATACONSUM.NS", "HINDALCO.NS", "INFY.NS", "GAIL.NS", "TECHM.NS", "BPCL.NS"]
        
    compiled_screen_data = []
    print(f"📋 Running multi-level structural matrix over {len(tickers)} assets...")
    
    for count, stock in enumerate(tickers, 1):
        data = engine.process_ticker_geometry(stock)
        if data:
            compiled_screen_data.append(data)
            print(f"   [+] Pattern Captured: {data['ticker']} | Zone: {data['patternZone']} | Dist: {data['distanceRemaining']}%")
            
            # HOOK UP YOUR EXISTING TELEGRAM SCRIPT HERE:
            if data["notificationTrigger"]:
                print(f"   🚨 PATTERN TOUCH ALERT: {data['ticker']} has hit trendline trigger at ₹{data['triggerPrice']} inside the {data['patternZone']}!")
                # execute_your_live_telegram_alert(
                #    f"🚨 PATTERN TOUCH ALERT: {data['ticker']} has hit trendline trigger at ₹{data['triggerPrice']} inside the {data['patternZone']}!"
                # )
                pass

    # Write out the clean JSON data payload for your separated HTML screen loader
    with open("trendline_screen.json", "w") as json_file:
        json.dump(compiled_screen_data, json_file, indent=4)
        
    print(f"\n==================================================================")
    print(f"✅ SUCCESS: trendline_screen.json updated with {len(compiled_screen_data)} matched rows.")
    print(f"==================================================================")

if __name__ == "__main__":
    synchronize_production_database()
