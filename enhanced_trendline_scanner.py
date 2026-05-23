#!/usr/bin/env python3
"""
Enhanced Trendline Scanner - Imaginary Vertical Line Method
Applying learned pattern recognition for 500-stock analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json
import time

class ImaginaryVerticalLineEngine:
    """
    Enhanced trendline engine using imaginary vertical line method
    Focus on CURRENT trigger points, not future predictions
    """
    
    def __init__(self, touch_tolerance=5.0, critical_threshold=1.0):
        """
        Initialize with learned parameters
        
        Args:
            touch_tolerance: ±5% tolerance for trendline approach (learned from teaching)
            critical_threshold: ±1% for critical entry signals
        """
        self.touch_tolerance = float(touch_tolerance)
        self.critical_threshold = float(critical_threshold)
        
    def get_sector_parameters(self, ticker):
        """
        Determine sector-specific parameters based on learned patterns
        """
        # Banking stocks need different parameters (learned from SBI/AXIS analysis)
        banking_stocks = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK', 
                         'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
        
        if any(bank in ticker.upper() for bank in banking_stocks):
            return {
                'order': 6,  # Banking sector uses order=6 (learned pattern)
                'sector': 'Banking',
                'typical_growth_range': '₹7-15/month'
            }
        else:
            return {
                'order': 12,  # Standard order for other sectors
                'sector': 'Non-Banking',
                'typical_growth_range': '₹10-50/month'
            }
    
    def calculate_imaginary_vertical_line_trigger(self, df, slope, intercept):
        """
        Apply imaginary vertical line method to get CURRENT trigger point
        
        This is the core learning: Focus on WHERE trendline IS NOW, not where it will be
        """
        # Get current month position (where we are NOW)
        current_month_idx = df['Price_Idx'].iloc[-1]
        
        # Calculate CURRENT trendline intersection (imaginary vertical line)
        current_trigger_price = (slope * current_month_idx) + intercept
        
        # This is the ONLY number that matters for entry decisions
        return {
            'current_month_position': int(current_month_idx),
            'current_trigger_price': float(current_trigger_price),
            'monthly_slope': float(slope),  # For reference only, not prediction
            'equation': f"Price = {slope:.4f} × Month + {intercept:.2f}"
        }
    
    def analyze_stock_with_imaginary_line_method(self, ticker):
        """
        Complete stock analysis using imaginary vertical line methodology
        """
        try:
            # 1. Get sector-specific parameters
            sector_params = self.get_sector_parameters(ticker)
            
            # 2. Download monthly data (8 years as learned)
            df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
            if df.empty or len(df) < 24:  # Need minimum 2 years
                return None
                
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()
            
            # 3. Find major bottoms using sector-specific order
            touchbacks = argrelextrema(low_prices, np.less, order=sector_params['order'])
            if len(touchbacks[0]) < 3:  # Need minimum 3 touches
                return None
            
            # 4. Use last 3-4 touches for most relevant trendline (learned pattern)
            num_touches = min(4, len(touchbacks[0]))
            recent_touches = touchbacks[0][-num_touches:]
            
            # Extract coordinates
            x_coords = [df['Price_Idx'].iloc[idx] for idx in recent_touches]
            y_coords = [low_prices[idx] for idx in recent_touches]
            
            # 5. Fit trendline
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            # 6. VALIDATE: Must be ascending (learned requirement)
            if slope <= 0:
                return None
            
            # 7. Apply imaginary vertical line method (CORE LEARNING)
            trigger_data = self.calculate_imaginary_vertical_line_trigger(df, slope, intercept)
            
            # 8. Get current price and calculate distance
            current_price = df['Close'].iloc[-1].item()
            current_trigger = trigger_data['current_trigger_price']
            
            distance_pct = ((current_price - current_trigger) / current_trigger) * 100
            
            # 9. Determine signal based on learned tolerance
            if abs(distance_pct) <= self.critical_threshold:
                signal_status = "CRITICAL_TOUCH"
                signal_color = "🎯"
                action = "BUY NOW"
            elif abs(distance_pct) <= self.touch_tolerance:
                signal_status = "WATCHLIST"
                signal_color = "👀"
                action = "MONITOR"
            else:
                return None  # Not near trendline, skip
            
            # 10. Calculate Fibonacci confluence (learned enhancement)
            confluence_data = self.calculate_fibonacci_confluence(df, recent_touches, current_trigger)
            
            # 11. Calculate risk management parameters
            stop_loss = current_trigger * 0.92  # 8% below trigger
            target_exit = current_trigger * 1.20  # 20% above trigger
            
            # 12. Touch point details for validation
            touch_points = []
            for i, touch_idx in enumerate(recent_touches):
                touch_date = df.index[touch_idx]
                touch_price = low_prices[touch_idx]
                touch_points.append({
                    'date': touch_date.strftime('%Y-%m-%d'),
                    'price': round(touch_price, 2),
                    'months_ago': int(trigger_data['current_month_position'] - df['Price_Idx'].iloc[touch_idx])
                })
            
            return {
                'ticker': ticker.replace('.NS', ''),
                'sector': sector_params['sector'],
                'current_analysis': {
                    'current_price': round(current_price, 2),
                    'trigger_price': round(current_trigger, 2),
                    'distance_pct': round(distance_pct, 2),
                    'signal_status': signal_status,
                    'signal_icon': signal_color,
                    'action': action
                },
                'imaginary_line_data': {
                    'current_month_position': trigger_data['current_month_position'],
                    'monthly_slope': round(trigger_data['monthly_slope'], 2),
                    'equation': trigger_data['equation'],
                    'note': 'This trigger price updates monthly as trendline moves up'
                },
                'fibonacci_confluence': confluence_data,
                'risk_management': {
                    'entry_zone': f"₹{current_trigger-20:.0f} - ₹{current_trigger+20:.0f}",
                    'stop_loss': round(stop_loss, 2),
                    'target_exit': round(target_exit, 2),
                    'risk_reward': '1:2.5'
                },
                'trendline_validation': {
                    'touch_points': touch_points,
                    'num_touches': len(recent_touches),
                    'trendline_strength': 'Strong' if len(recent_touches) >= 4 else 'Good',
                    'slope_direction': 'Ascending' if slope > 0 else 'Descending'
                },
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def calculate_fibonacci_confluence(self, df, touch_indices, current_trigger):
        """
        Calculate Fibonacci confluence for current trigger point
        """
        try:
            # Get last touch and find swing high after it
            last_touch_idx = touch_indices[-1]
            last_touch_price = df['Low'].iloc[last_touch_idx].item()
            
            # Find swing high after last touch
            data_after_touch = df.iloc[last_touch_idx:]
            swing_high = data_after_touch['High'].max().item()
            
            # Calculate Fibonacci levels
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return {'confluence_score': 0, 'note': 'No valid Fibonacci range'}
            
            fib_levels = {
                '23.6%': swing_high - (fib_range * 0.236),
                '38.2%': swing_high - (fib_range * 0.382),
                '50.0%': swing_high - (fib_range * 0.500),
                '61.8%': swing_high - (fib_range * 0.618),
                '78.6%': swing_high - (fib_range * 0.786)
            }
            
            # Find closest Fibonacci level to current trigger
            closest_level = None
            min_distance = float('inf')
            
            for level_name, fib_price in fib_levels.items():
                distance_pct = abs((current_trigger - fib_price) / fib_price) * 100
                if distance_pct < min_distance:
                    min_distance = distance_pct
                    closest_level = level_name
            
            # Score confluence (learned from teaching)
            if min_distance <= 1.0:
                confluence_score = 10
                confluence_note = f"PERFECT confluence with {closest_level}"
            elif min_distance <= 2.0:
                confluence_score = 7
                confluence_note = f"GOOD confluence with {closest_level}"
            elif min_distance <= 5.0:
                confluence_score = 5
                confluence_note = f"MODERATE confluence with {closest_level}"
            else:
                confluence_score = 2
                confluence_note = f"WEAK confluence"
            
            return {
                'confluence_score': confluence_score,
                'closest_fib_level': closest_level,
                'distance_to_fib': round(min_distance, 2),
                'confluence_note': confluence_note,
                'fib_levels': {level: round(price, 2) for level, price in fib_levels.items()}
            }
            
        except Exception:
            return {'confluence_score': 0, 'note': 'Fibonacci calculation failed'}

def scan_nifty_500_with_imaginary_lines():
    """
    Scan all Nifty 500 stocks using imaginary vertical line method
    """
    print("🎯 NIFTY 500 IMAGINARY VERTICAL LINE SCANNER")
    print("="*70)
    print("📚 APPLYING: Learned trendline methodology")
    print("🎯 FOCUS: Current trigger points (not future predictions)")
    print("📊 METHOD: Imaginary vertical line intersections")
    
    # Initialize engine
    engine = ImaginaryVerticalLineEngine()
    
    # Nifty 500 tickers (sample for testing - add full list)
    nifty_500_sample = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'NESTLEIND.NS', 'ULTRACEMCO.NS',
        'TITAN.NS', 'SUNPHARMA.NS', 'WIPRO.NS', 'MARUTI.NS', 'POWERGRID.NS'
    ]
    
    results = []
    critical_signals = []
    watchlist_signals = []
    
    print(f"\n🔍 SCANNING {len(nifty_500_sample)} STOCKS...")
    print("-" * 50)
    
    for i, ticker in enumerate(nifty_500_sample, 1):
        try:
            print(f"   Processing {i:2d}/{len(nifty_500_sample)}: {ticker.replace('.NS', '')}", end="")
            
            # Analyze stock
            analysis = engine.analyze_stock_with_imaginary_line_method(ticker)
            
            if analysis:
                results.append(analysis)
                
                if analysis['current_analysis']['signal_status'] == 'CRITICAL_TOUCH':
                    critical_signals.append(analysis)
                    print(f" ✅ 🎯 CRITICAL")
                else:
                    watchlist_signals.append(analysis)
                    print(f" ✅ 👀 WATCHLIST")
            else:
                print(f" ❌ No signal")
                
        except Exception as e:
            print(f" ❌ Error")
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    # Sort results by distance (closest to trendline first)
    results.sort(key=lambda x: abs(x['current_analysis']['distance_pct']))
    
    print(f"\n🎯 SCAN RESULTS SUMMARY")
    print("-" * 50)
    print(f"📊 Total Analyzed: {len(nifty_500_sample)}")
    print(f"🎯 Critical Signals: {len(critical_signals)}")
    print(f"👀 Watchlist Signals: {len(watchlist_signals)}")
    print(f"📈 Total Opportunities: {len(results)}")
    
    # Display critical signals first
    if critical_signals:
        print(f"\n🎯 CRITICAL ENTRY SIGNALS (±1%)")
        print("-" * 50)
        for signal in critical_signals:
            curr = signal['current_analysis']
            print(f"   {signal['ticker']:12} | ₹{curr['current_price']:8.2f} | Trigger: ₹{curr['trigger_price']:8.2f} | {curr['distance_pct']:+5.1f}%")
    
    # Display watchlist signals
    if watchlist_signals:
        print(f"\n👀 WATCHLIST SIGNALS (±5%)")
        print("-" * 50)
        for signal in watchlist_signals[:10]:  # Top 10
            curr = signal['current_analysis']
            fib = signal['fibonacci_confluence']
            print(f"   {signal['ticker']:12} | ₹{curr['current_price']:8.2f} | Trigger: ₹{curr['trigger_price']:8.2f} | {curr['distance_pct']:+5.1f}% | Fib: {fib['confluence_score']}/10")
    
    # Save results to JSON
    output_data = {
        'scan_timestamp': datetime.now().isoformat(),
        'methodology': 'Imaginary Vertical Line Method',
        'total_scanned': len(nifty_500_sample),
        'critical_signals': len(critical_signals),
        'watchlist_signals': len(watchlist_signals),
        'results': results
    }
    
    with open('trendline_screen.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to: trendline_screen.json")
    print(f"🎯 Ready for HTML dashboard display!")
    
    return results

if __name__ == "__main__":
    scan_nifty_500_with_imaginary_lines()