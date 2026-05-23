#!/usr/bin/env python3
"""
Diagnostic Analysis: Check Current Trendline Signals
Analyze what signals our system is generating right now
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

class TrendlineDiagnostic:
    """
    Diagnostic tool to analyze current trendline signals
    """
    
    def __init__(self):
        self.results = []
        
    def get_sector_parameters(self, ticker):
        """Get sector-specific parameters"""
        banking_stocks = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK']
        if any(bank in ticker.upper() for bank in banking_stocks):
            return {'order': 6, 'sector': 'Banking'}
        else:
            return {'order': 8, 'sector': 'Non-Banking'}
    
    def analyze_current_trendline(self, ticker):
        """Analyze current trendline status for a stock"""
        try:
            print(f"\n🔍 ANALYZING: {ticker}")
            print("-" * 40)
            
            # Download data
            df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
            if df.empty:
                print("❌ No data available")
                return None
            
            # Create monthly data
            monthly_data = df.resample('M').agg({
                'Open': 'first',
                'High': 'max', 
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            if len(monthly_data) < 24:
                print("❌ Insufficient monthly data")
                return None
            
            monthly_data['Price_Idx'] = np.arange(len(monthly_data))
            low_prices = monthly_data['Low'].values.flatten()
            
            # Get sector parameters
            sector_params = self.get_sector_parameters(ticker)
            print(f"📊 Sector: {sector_params['sector']} (order={sector_params['order']})")
            
            # Find major bottoms
            touchbacks = argrelextrema(low_prices, np.less, order=sector_params['order'])
            print(f"📍 Found {len(touchbacks[0])} major touch points")
            
            if len(touchbacks[0]) < 3:
                print("❌ Need minimum 3 touch points")
                return None
            
            # Use last 3-4 touches
            num_touches = min(4, len(touchbacks[0]))
            recent_touches = touchbacks[0][-num_touches:]
            
            print(f"📌 Using last {num_touches} touches:")
            for i, touch_idx in enumerate(recent_touches):
                touch_date = monthly_data.index[touch_idx]
                touch_price = low_prices[touch_idx]
                print(f"   Touch {i+1}: {touch_date.strftime('%Y-%m')} at ₹{touch_price:.2f}")
            
            # Extract coordinates
            x_coords = [monthly_data['Price_Idx'].iloc[idx] for idx in recent_touches]
            y_coords = [low_prices[idx] for idx in recent_touches]
            
            # Fit trendline
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            print(f"📈 Trendline: slope = ₹{slope:.2f}/month")
            
            if slope <= 0:
                print("❌ Descending trendline - not suitable")
                return None
            
            # Calculate current trigger using imaginary vertical line
            current_month_idx = monthly_data['Price_Idx'].iloc[-1]
            current_trigger = (slope * current_month_idx) + intercept
            
            # Get current price
            current_price = df['Close'].iloc[-1]
            distance_pct = ((current_price - current_trigger) / current_trigger) * 100
            
            print(f"💰 Current Price: ₹{current_price:.2f}")
            print(f"🎯 Trendline Trigger: ₹{current_trigger:.2f}")
            print(f"📏 Distance: {distance_pct:+.2f}%")
            
            # Calculate R-squared
            predicted_prices = [slope * x + intercept for x in x_coords]
            correlation = np.corrcoef(y_coords, predicted_prices)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0
            print(f"📊 R-squared: {r_squared:.3f}")
            
            # Calculate Fibonacci confluence
            confluence_score = self.calculate_fibonacci_confluence(monthly_data, recent_touches, current_trigger)
            print(f"🎯 Fibonacci Confluence: {confluence_score}/10")
            
            # Determine signal status
            signal_status = "NO SIGNAL"
            if abs(distance_pct) <= 1.0:
                signal_status = "🎯 CRITICAL TOUCH"
            elif abs(distance_pct) <= 5.0:
                signal_status = "👀 WATCHLIST"
            elif abs(distance_pct) <= 15.0:
                signal_status = "📊 MONITOR"
            
            print(f"🚦 Signal Status: {signal_status}")
            
            # Check entry criteria
            entry_criteria = {
                'distance_ok': abs(distance_pct) <= 5.0,
                'confluence_ok': confluence_score >= 5,
                'r_squared_ok': r_squared >= 0.7,
                'touches_ok': num_touches >= 3
            }
            
            print(f"\n✅ ENTRY CRITERIA CHECK:")
            print(f"   Distance ≤5%: {'✅' if entry_criteria['distance_ok'] else '❌'} ({distance_pct:+.1f}%)")
            print(f"   Confluence ≥5: {'✅' if entry_criteria['confluence_ok'] else '❌'} ({confluence_score}/10)")
            print(f"   R-squared ≥0.7: {'✅' if entry_criteria['r_squared_ok'] else '❌'} ({r_squared:.3f})")
            print(f"   Touches ≥3: {'✅' if entry_criteria['touches_ok'] else '❌'} ({num_touches})")
            
            all_criteria_met = all(entry_criteria.values())
            print(f"\n🎯 ENTRY SIGNAL: {'✅ BUY' if all_criteria_met else '❌ NO ENTRY'}")
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'trigger_price': current_trigger,
                'distance_pct': distance_pct,
                'confluence_score': confluence_score,
                'r_squared': r_squared,
                'num_touches': num_touches,
                'monthly_growth': slope,
                'signal_status': signal_status,
                'entry_signal': all_criteria_met,
                'criteria': entry_criteria
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {str(e)}")
            return None
    
    def calculate_fibonacci_confluence(self, monthly_data, touch_indices, trigger_price):
        """Calculate Fibonacci confluence score"""
        try:
            if len(touch_indices) < 2:
                return 3
            
            last_touch_idx = touch_indices[-1]
            last_touch_price = monthly_data['Low'].iloc[last_touch_idx]
            
            # Find swing high after last touch
            data_after_touch = monthly_data.iloc[last_touch_idx:]
            if len(data_after_touch) == 0:
                return 3
            
            swing_high = data_after_touch['High'].max()
            
            # Calculate Fibonacci levels
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return 3
            
            fib_levels = {
                '23.6%': swing_high - (fib_range * 0.236),
                '38.2%': swing_high - (fib_range * 0.382),
                '50.0%': swing_high - (fib_range * 0.500),
                '61.8%': swing_high - (fib_range * 0.618),
                '78.6%': swing_high - (fib_range * 0.786)
            }
            
            # Find closest level
            min_distance = float('inf')
            closest_level = None
            
            for level_name, fib_price in fib_levels.items():
                distance_pct = abs((trigger_price - fib_price) / fib_price) * 100
                if distance_pct < min_distance:
                    min_distance = distance_pct
                    closest_level = level_name
            
            # Score confluence
            if min_distance <= 1.0 and closest_level in ['38.2%', '50.0%', '61.8%']:
                return 10
            elif min_distance <= 2.0:
                return 7
            elif min_distance <= 5.0 and closest_level in ['38.2%', '50.0%', '61.8%']:
                return 5
            else:
                return 2
                
        except Exception:
            return 3
    
    def run_diagnostic(self, tickers):
        """Run diagnostic on multiple stocks"""
        print("🎯 TRENDLINE DIAGNOSTIC ANALYSIS")
        print("="*70)
        print("📅 Analysis Date:", datetime.now().strftime('%Y-%m-%d'))
        print("📚 Methodology: Imaginary Vertical Line Method")
        
        results = []
        entry_signals = []
        watchlist_signals = []
        
        for ticker in tickers:
            result = self.analyze_current_trendline(ticker)
            if result:
                results.append(result)
                if result['entry_signal']:
                    entry_signals.append(result)
                elif abs(result['distance_pct']) <= 15:
                    watchlist_signals.append(result)
        
        # Summary
        print(f"\n🏆 DIAGNOSTIC SUMMARY")
        print("="*70)
        print(f"📊 Total Analyzed: {len(tickers)}")
        print(f"✅ Valid Trendlines: {len(results)}")
        print(f"🎯 Entry Signals: {len(entry_signals)}")
        print(f"👀 Watchlist Signals: {len(watchlist_signals)}")
        
        # Entry signals
        if entry_signals:
            print(f"\n🎯 CURRENT ENTRY SIGNALS:")
            print("-" * 50)
            for signal in entry_signals:
                print(f"   {signal['ticker']:12} | ₹{signal['current_price']:8.2f} | Trigger: ₹{signal['trigger_price']:8.2f} | {signal['distance_pct']:+5.1f}% | Conf: {signal['confluence_score']}/10")
        
        # Watchlist signals
        if watchlist_signals:
            print(f"\n👀 WATCHLIST SIGNALS (Within 15%):")
            print("-" * 50)
            for signal in sorted(watchlist_signals, key=lambda x: abs(x['distance_pct']))[:10]:
                print(f"   {signal['ticker']:12} | ₹{signal['current_price']:8.2f} | Trigger: ₹{signal['trigger_price']:8.2f} | {signal['distance_pct']:+5.1f}% | Conf: {signal['confluence_score']}/10")
        
        # Analysis insights
        print(f"\n💡 SYSTEM INSIGHTS:")
        if len(entry_signals) == 0:
            print("   • No current entry signals - system is highly selective")
            print("   • This indicates strong quality control")
            print("   • Wait for proper trendline touches")
        
        if len(results) > 0:
            avg_confluence = np.mean([r['confluence_score'] for r in results])
            avg_r_squared = np.mean([r['r_squared'] for r in results])
            print(f"   • Average Confluence Score: {avg_confluence:.1f}/10")
            print(f"   • Average R-squared: {avg_r_squared:.3f}")
        
        return results

def run_diagnostic():
    """Run diagnostic analysis"""
    
    # Test stocks
    test_tickers = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'TITAN.NS', 'WIPRO.NS'
    ]
    
    diagnostic = TrendlineDiagnostic()
    results = diagnostic.run_diagnostic(test_tickers)
    
    return results

if __name__ == "__main__":
    run_diagnostic()