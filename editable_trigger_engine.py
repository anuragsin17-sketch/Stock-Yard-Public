#!/usr/bin/env python3
"""
Enhanced Geometric Engine with Editable Trigger Points
Allows manual override of calculated trigger prices
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import json
import os
from datetime import datetime, timedelta

class EditableTriggerEngine:
    def __init__(self, position_size=50000.0, sl_pct=8.0, touch_tolerance=5.0):
        """
        Enhanced engine with editable trigger points
        """
        self.capital_per_trade = float(position_size)
        self.sl_multiplier = 1.0 - (float(sl_pct) / 100.0)
        self.touch_tolerance = float(touch_tolerance)
        
        # Load custom trigger overrides
        self.trigger_overrides = self.load_trigger_overrides()
    
    def load_trigger_overrides(self):
        """Load custom trigger price overrides from JSON file"""
        try:
            if os.path.exists('trigger_overrides.json'):
                with open('trigger_overrides.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load trigger overrides: {e}")
        return {}
    
    def save_trigger_overrides(self):
        """Save trigger overrides to JSON file"""
        try:
            with open('trigger_overrides.json', 'w') as f:
                json.dump(self.trigger_overrides, f, indent=4)
        except Exception as e:
            print(f"Error saving trigger overrides: {e}")
    
    def set_custom_trigger(self, ticker, trigger_price, notes="Manual override"):
        """
        Set a custom trigger price for a specific stock
        
        Args:
            ticker: Stock symbol (e.g., "ASIANPAINT")
            trigger_price: Custom trigger price
            notes: Optional notes about why this trigger was set
        """
        clean_ticker = ticker.replace(".NS", "")
        
        self.trigger_overrides[clean_ticker] = {
            "customTrigger": float(trigger_price),
            "setDate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "notes": notes,
            "isActive": True
        }
        
        self.save_trigger_overrides()
        print(f"✅ Custom trigger set for {clean_ticker}: ₹{trigger_price}")
    
    def remove_custom_trigger(self, ticker):
        """Remove custom trigger for a stock"""
        clean_ticker = ticker.replace(".NS", "")
        
        if clean_ticker in self.trigger_overrides:
            del self.trigger_overrides[clean_ticker]
            self.save_trigger_overrides()
            print(f"✅ Custom trigger removed for {clean_ticker}")
        else:
            print(f"❌ No custom trigger found for {clean_ticker}")
    
    def get_effective_trigger(self, ticker, calculated_trigger):
        """
        Get the effective trigger price (custom override or calculated)
        
        Returns:
            dict with trigger info
        """
        clean_ticker = ticker.replace(".NS", "")
        
        if clean_ticker in self.trigger_overrides:
            override = self.trigger_overrides[clean_ticker]
            if override.get("isActive", True):
                return {
                    "price": override["customTrigger"],
                    "source": "CUSTOM",
                    "setDate": override["setDate"],
                    "notes": override["notes"],
                    "originalCalculated": calculated_trigger
                }
        
        return {
            "price": calculated_trigger,
            "source": "CALCULATED",
            "setDate": None,
            "notes": "Algorithm calculated",
            "originalCalculated": calculated_trigger
        }
    
    def find_swing_high_after_touch(self, df, last_touch_idx):
        """Find swing high after last touch"""
        data_after_touch = df.iloc[last_touch_idx:]
        
        if len(data_after_touch) < 3:
            return df['High'].max().item()
        
        highs = data_after_touch['High'].values
        maxima_indices = argrelextrema(highs, np.greater, order=3)[0]
        
        if len(maxima_indices) > 0:
            return data_after_touch['High'].iloc[maxima_indices].max().item()
        else:
            return data_after_touch['High'].max().item()
    
    def process_ticker_geometry(self, ticker: str):
        """
        Enhanced process with editable triggers
        """
        try:
            # 1. Fetch data and run standard algorithm
            df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
            if df.empty or len(df) < 24:
                return None
                
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()
            
            # 2. Find touchbacks
            touchbacks = argrelextrema(low_prices, np.less, order=12)
            if len(touchbacks[0]) < 3:
                return None
                
            # 3. Fit trendline
            num_touches = min(4, len(touchbacks[0]))
            x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
            y_anchors = low_prices[touchbacks[0][-num_touches:]]
            slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
            
            if slope <= 0:
                return None
            
            # 4. Calculate wave and Fibonacci
            last_touch_idx = touchbacks[0][-1]
            last_touch_price = low_prices[last_touch_idx]
            swing_high_after_touch = self.find_swing_high_after_touch(df, last_touch_idx)
            
            wave_base_origin = last_touch_price
            wave_peak_ceiling = swing_high_after_touch
            total_wave_range = wave_peak_ceiling - wave_base_origin
            
            if total_wave_range <= 0:
                return None
            
            # 5. Calculate standard trigger
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            calculated_trigger = (slope * current_bar_idx) + intercept
            
            # 6. Get effective trigger (custom or calculated)
            trigger_info = self.get_effective_trigger(ticker, calculated_trigger)
            effective_trigger = trigger_info["price"]
            
            # 7. Calculate distance using effective trigger
            pct_distance_to_line = ((current_close - effective_trigger) / effective_trigger) * 100
            
            # 8. Check if within tolerance
            if not (-self.touch_tolerance <= pct_distance_to_line <= self.touch_tolerance):
                return None
            
            # 9. Calculate Fibonacci levels
            upcoming_line_fib_pct = ((wave_peak_ceiling - effective_trigger) / total_wave_range) * 100
            
            if upcoming_line_fib_pct < 38.2:
                return None
            
            # 10. Fibonacci confluence analysis
            fib_236 = wave_peak_ceiling - (total_wave_range * 0.236)
            fib_382 = wave_peak_ceiling - (total_wave_range * 0.382)
            fib_500 = wave_peak_ceiling - (total_wave_range * 0.500)
            fib_618 = wave_peak_ceiling - (total_wave_range * 0.618)
            fib_786 = wave_peak_ceiling - (total_wave_range * 0.786)
            
            fib_levels = {
                "23.6%": fib_236, "38.2%": fib_382, "50.0%": fib_500,
                "61.8%": fib_618, "78.6%": fib_786
            }
            
            # Find closest Fib level to effective trigger
            fib_distances = {}
            for level_name, fib_price in fib_levels.items():
                distance_pct = abs((effective_trigger - fib_price) / fib_price) * 100
                fib_distances[level_name] = distance_pct
            
            closest_fib_level = min(fib_distances, key=fib_distances.get)
            closest_fib_distance = fib_distances[closest_fib_level]
            
            # 11. Confluence scoring
            confluence_score = 0
            confluence_notes = []
            
            if closest_fib_distance <= 1.0 and closest_fib_level in ["38.2%", "50.0%", "61.8%"]:
                confluence_score = 10
                confluence_notes.append(f"PERFECT confluence with {closest_fib_level}")
            elif closest_fib_distance <= 2.0:
                confluence_score = 7
                confluence_notes.append(f"GOOD confluence with {closest_fib_level}")
            elif closest_fib_distance <= 5.0 and closest_fib_level in ["38.2%", "50.0%", "61.8%"]:
                confluence_score = 5
                confluence_notes.append(f"MODERATE confluence with {closest_fib_level}")
            else:
                confluence_score = 2
                confluence_notes.append(f"Weak confluence")
            
            if closest_fib_level == "61.8%" and closest_fib_distance <= 3.0:
                confluence_score += 3
                confluence_notes.append("GOLDEN RATIO BONUS")
            
            # 12. Position sizing
            calculated_stop_loss = effective_trigger * self.sl_multiplier
            total_shares_to_buy = int(self.capital_per_trade // effective_trigger)
            
            # 13. Alert trigger
            is_alert_active = abs(pct_distance_to_line) <= 1.0
            
            # 14. Zone classification
            if 38.2 <= upcoming_line_fib_pct < 50.0:
                zone_tag = "38.2% (Institutional Pocket)"
            elif 50.0 <= upcoming_line_fib_pct < 61.8:
                zone_tag = "50.0% (Equilibrium Baseline)"
            elif 61.8 <= upcoming_line_fib_pct < 100.0:
                zone_tag = "61.8% (Golden Ratio Floor)"
            else:
                zone_tag = "100.0% (Full Capitulation Reset)"
            
            return {
                "ticker": ticker.replace(".NS", ""),
                "currentSignal": {
                    "isActive": True,
                    "currentPrice": round(current_close, 2),
                    "triggerPrice": round(effective_trigger, 2),
                    "distanceRemaining": round(abs(pct_distance_to_line), 2),
                    "fibLevelMatch": f"{round(upcoming_line_fib_pct, 2)}%",
                    "patternZone": zone_tag,
                    "confluenceScore": confluence_score,
                    "confluenceNotes": confluence_notes,
                    "notificationTrigger": bool(is_alert_active)
                },
                "triggerInfo": {
                    "effectivePrice": round(effective_trigger, 2),
                    "source": trigger_info["source"],
                    "isCustom": trigger_info["source"] == "CUSTOM",
                    "setDate": trigger_info["setDate"],
                    "notes": trigger_info["notes"],
                    "originalCalculated": round(trigger_info["originalCalculated"], 2)
                },
                "positionSizing": {
                    "allocatedAmount": float(self.capital_per_trade),
                    "sharesToBuy": int(total_shares_to_buy),
                    "strictStopLoss": round(calculated_stop_loss, 2),
                    "pivotTargetExit": round(wave_peak_ceiling, 2)
                },
                "fullFibGridPrices": {
                    "level_236": round(fib_236, 2),
                    "level_382": round(fib_382, 2),
                    "level_500": round(fib_500, 2),
                    "level_618": round(fib_618, 2),
                    "level_786": round(fib_786, 2),
                    "level_1000": round(wave_base_origin, 2)
                },
                "fibConfluence": {
                    "closestLevel": closest_fib_level,
                    "distanceToClosest": round(closest_fib_distance, 2),
                    "confluenceScore": confluence_score,
                    "confluenceNotes": confluence_notes,
                    "allDistances": {level: round(dist, 2) for level, dist in fib_distances.items()}
                }
            }
            
        except Exception as e:
            pass
        return None

    def list_custom_triggers(self):
        """List all active custom triggers"""
        if not self.trigger_overrides:
            print("No custom triggers set.")
            return
        
        print("📋 ACTIVE CUSTOM TRIGGERS:")
        print("="*60)
        for ticker, override in self.trigger_overrides.items():
            if override.get("isActive", True):
                print(f"{ticker:12s} ₹{override['customTrigger']:>8.2f} | Set: {override['setDate']}")
                print(f"             Notes: {override['notes']}")
                print()

if __name__ == "__main__":
    # Example usage
    engine = EditableTriggerEngine()
    
    # Set custom triggers
    engine.set_custom_trigger("ASIANPAINT", 2620.00, "Manual analysis - better entry point")
    engine.set_custom_trigger("HDFCBANK", 780.00, "Adjusted for recent support level")
    
    # List custom triggers
    engine.list_custom_triggers()
    
    # Test with custom trigger
    result = engine.process_ticker_geometry("ASIANPAINT.NS")
    if result:
        trigger_info = result['triggerInfo']
        print(f"\n🎯 ASIANPAINT Trigger Analysis:")
        print(f"   Effective Trigger: ₹{trigger_info['effectivePrice']} ({trigger_info['source']})")
        print(f"   Original Calculated: ₹{trigger_info['originalCalculated']}")
        if trigger_info['isCustom']:
            print(f"   Custom Set: {trigger_info['setDate']}")
            print(f"   Notes: {trigger_info['notes']}")