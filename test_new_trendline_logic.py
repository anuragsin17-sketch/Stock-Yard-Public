"""
Test New Trendline Logic on Last 1 Year Data
This script backtests the improved trendline + Fibonacci strategy
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json

class ImprovedTrendlineEngine:
    def __init__(self):
        self.results = []
        
    def find_swing_high_after_touch(self, df, last_touch_idx):
        """Find the swing high AFTER the last trendline touch"""
        # Get data after the last touch
        data_after_touch = df.iloc[last_touch_idx:]
        
        if len(data_after_touch) < 3:
            return df['High'].max()  # Fallback to max if not enough data
        
        # Find local maxima after the touch
        highs = data_after_touch['High'].values
        maxima_indices = argrelextrema(highs, np.greater, order=3)[0]
        
        if len(maxima_indices) > 0:
            # Return the highest peak after touch
            return data_after_touch['High'].iloc[maxima_indices].max()
        else:
            # Return max high after touch
            return data_after_touch['High'].max()
    
    def analyze_stock(self, ticker: str, test_date: datetime):
        """Analyze stock with new logic at a specific date"""
        try:
            # Fetch historical data up to test_date
            end_date = test_date
            start_date = end_date - timedelta(days=15*365)  # 15 years
            
            df = yf.download(ticker, start=start_date, end=end_date, 
                           interval="1mo", auto_adjust=True, progress=False)
            
            if df.empty or len(df) < 36:
                return None
            
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()
            
            # Find monthly lows (local minima)
            touchbacks = argrelextrema(low_prices, np.less, order=12)
            if len(touchbacks[0]) < 3:
                return None
            
            # Use last 3-4 touch points for trendline
            x_anchors = df['Price_Idx'].iloc[touchbacks[0][-4:]].values
            y_anchors = low_prices[touchbacks[0][-4:]]
            
            # Fit trendline
            slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
            
            # Validate ascending trendline
            if slope <= 0:
                return None
            
            # Get last touch point
            last_touch_idx = touchbacks[0][-1]
            last_touch_price = low_prices[last_touch_idx]
            
            # Find swing high AFTER last touch (not all-time high)
            swing_high_after_touch = self.find_swing_high_after_touch(df, last_touch_idx)
            
            # Calculate Fibonacci from last touch to swing high after
            wave_base = last_touch_price
            wave_peak = swing_high_after_touch
            total_range = wave_peak - wave_base
            
            if total_range <= 0:
                return None
            
            # Project trendline to current date (last bar in our test data)
            current_bar_idx = df['Price_Idx'].iloc[-1]
            trendline_price_today = (slope * current_bar_idx) + intercept
            current_price = df['Close'].iloc[-1]
            
            # Calculate where trendline sits in Fibonacci grid
            fib_position_pct = ((wave_peak - trendline_price_today) / total_range) * 100
            
            # NEW FILTER: Only accept if Fibonacci position is 38.2% to 100%+
            if fib_position_pct < 38.2:
                return None
            
            # Calculate distance to trendline
            distance_pct = ((current_price - trendline_price_today) / trendline_price_today) * 100
            
            # NEW FILTER: Only accept if within ±2% of trendline
            if not (-2.0 <= distance_pct <= 2.0):
                return None
            
            # Classify Fibonacci zone
            if 38.2 <= fib_position_pct < 50:
                zone = "38.2% Institutional Pocket"
            elif 50 <= fib_position_pct < 61.8:
                zone = "50% Equilibrium Zone"
            elif 61.8 <= fib_position_pct < 100:
                zone = "61.8% Golden Ratio Floor"
            else:
                zone = "100% Full Capitulation Reset"
            
            # Calculate Fibonacci levels
            fib_236 = wave_peak - (total_range * 0.236)
            fib_382 = wave_peak - (total_range * 0.382)
            fib_500 = wave_peak - (total_range * 0.500)
            fib_618 = wave_peak - (total_range * 0.618)
            
            return {
                'ticker': ticker.replace('.NS', ''),
                'test_date': test_date.strftime('%Y-%m-%d'),
                'current_price': round(current_price, 2),
                'trendline_price': round(trendline_price_today, 2),
                'distance_pct': round(distance_pct, 2),
                'fib_position': round(fib_position_pct, 2),
                'zone': zone,
                'entry': round(trendline_price_today, 2),
                'stop_loss': round(trendline_price_today * 0.92, 2),  # 8% below
                'target': round(swing_high_after_touch, 2),
                'last_touch': round(last_touch_price, 2),
                'swing_high': round(swing_high_after_touch, 2),
                'fib_levels': {
                    '236': round(fib_236, 2),
                    '382': round(fib_382, 2),
                    '500': round(fib_500, 2),
                    '618': round(fib_618, 2),
                    '1000': round(wave_base, 2)
                }
            }
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return None
    
    def backtest_year(self, tickers, start_date, end_date):
        """Backtest the strategy over a date range"""
        print(f"\n{'='*80}")
        print(f"BACKTESTING NEW TRENDLINE LOGIC")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"{'='*80}\n")
        
        # Test at monthly intervals
        test_dates = pd.date_range(start=start_date, end=end_date, freq='MS')
        
        all_signals = []
        
        for test_date in test_dates:
            print(f"\n📅 Testing Date: {test_date.strftime('%Y-%m-%d')}")
            print("-" * 80)
            
            month_signals = []
            
            for ticker in tickers:
                result = self.analyze_stock(ticker, test_date)
                if result:
                    month_signals.append(result)
                    print(f"✅ {result['ticker']:12} | Entry: ₹{result['entry']:8.2f} | "
                          f"Target: ₹{result['target']:8.2f} | Zone: {result['zone']}")
            
            if month_signals:
                all_signals.extend(month_signals)
                print(f"\n📊 Found {len(month_signals)} signals this month")
            else:
                print("❌ No signals found this month")
        
        return all_signals

def main():
    print("🚀 Starting New Trendline Logic Backtest...")
    
    # Load Nifty 500 tickers
    try:
        df = pd.read_csv('ind_nifty500list.csv')
        tickers = [str(t).strip() + ".NS" for t in df['Symbol'].tolist()[:50]]  # Test on first 50
        print(f"✅ Loaded {len(tickers)} tickers for testing")
    except:
        print("⚠️ Using fallback ticker list")
        tickers = ["SBIN.NS", "AXISBANK.NS", "TITAN.NS", "ICICIBANK.NS", 
                  "HDFCBANK.NS", "INFY.NS", "TCS.NS", "RELIANCE.NS"]
    
    # Test period: Last 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    engine = ImprovedTrendlineEngine()
    signals = engine.backtest_year(tickers, start_date, end_date)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"BACKTEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total Signals Generated: {len(signals)}")
    
    if signals:
        # Group by zone
        zones = {}
        for signal in signals:
            zone = signal['zone']
            if zone not in zones:
                zones[zone] = []
            zones[zone].append(signal)
        
        print(f"\n📊 Signals by Fibonacci Zone:")
        for zone, zone_signals in zones.items():
            print(f"  {zone}: {len(zone_signals)} signals")
        
        # Calculate potential returns
        print(f"\n💰 Potential Returns Analysis:")
        total_potential = 0
        for signal in signals:
            potential_return = ((signal['target'] - signal['entry']) / signal['entry']) * 100
            total_potential += potential_return
        
        avg_potential = total_potential / len(signals)
        print(f"  Average Potential Return: {avg_potential:.2f}%")
        
        # Save results
        with open('new_trendline_backtest_results.json', 'w') as f:
            json.dump(signals, f, indent=2)
        print(f"\n✅ Results saved to: new_trendline_backtest_results.json")
    else:
        print("\n⚠️ No signals found in the test period")
        print("This might indicate:")
        print("  - Filters are too strict")
        print("  - Market conditions didn't meet criteria")
        print("  - Need to adjust parameters")

if __name__ == "__main__":
    main()
