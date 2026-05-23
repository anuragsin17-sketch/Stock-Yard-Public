import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

class MacroInstitutionalEngine:
    def __init__(self, position_size=50000.0, sl_pct=8.0, touch_tolerance=5.0):
        """
        Initializes your precise pattern scanning and risk allocation matrices.
        
        Args:
            position_size: Capital allocated per trade (default: ₹50,000)
            sl_pct: Stop loss percentage below trendline (default: 8%)
            touch_tolerance: Percentage tolerance for trendline touch detection (default: ±5%)
        """
        self.capital_per_trade = float(position_size)
        self.sl_multiplier = 1.0 - (float(sl_pct) / 100.0)
        self.touch_tolerance = float(touch_tolerance)

    def find_swing_high_after_touch(self, df, last_touch_idx):
        """
        Find the swing high AFTER the last trendline touch (not all-time high).
        This gives a realistic target based on recent price action.
        """
        # Get data after the last touch
        data_after_touch = df.iloc[last_touch_idx:]
        
        if len(data_after_touch) < 3:
            return df['High'].max().item()  # Fallback to max if not enough data
        
        # Find local maxima after the touch
        highs = data_after_touch['High'].values
        maxima_indices = argrelextrema(highs, np.greater, order=3)[0]
        
        if len(maxima_indices) > 0:
            # Return the highest peak after touch
            return data_after_touch['High'].iloc[maxima_indices].max().item()
        else:
            # Return max high after touch
            return data_after_touch['High'].max().item()

    def process_ticker_geometry(self, ticker: str):
        """
        NEW IMPROVED LOGIC:
        - Uses monthly trendline with daily precision
        - Finds swing high AFTER last touch (not all-time high)
        - Accepts only stocks within ±2% of trendline (touch = entry)
        - Filters for Fibonacci institutional zones (38.2% to 100%)
        - Validates ascending trendline with minimum 3 touches
        """
        try:
            # 1. Fetch long-term monthly historical candle data
            df = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True, progress=False)
            if df.empty or len(df) < 36: 
                return None
                
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()
            
            # 2. Extract major multi-year visual bottoms (12-month cyclical radius)
            touchbacks = argrelextrema(low_prices, np.less, order=12)
            if len(touchbacks[0]) < 3:  # Need minimum 3 touches
                return None
                
            # 3. Fit trendline using last 3-4 major touches
            num_touches = min(4, len(touchbacks[0]))
            x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
            y_anchors = low_prices[touchbacks[0][-num_touches:]]
            slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
            
            # 4. VALIDATE: Trendline must be ascending
            if slope <= 0:
                return None
            
            # 5. Get last trendline touch point
            last_touch_idx = touchbacks[0][-1]
            last_touch_price = low_prices[last_touch_idx]
            
            # 6. Find swing high AFTER last touch (not all-time high)
            swing_high_after_touch = self.find_swing_high_after_touch(df, last_touch_idx)
            
            # 7. Calculate Fibonacci from last touch to swing high after
            wave_base_origin = last_touch_price
            wave_peak_ceiling = swing_high_after_touch
            total_wave_range = wave_peak_ceiling - wave_base_origin
            
            if total_wave_range <= 0: 
                return None
            
            # 8. Project trendline to current date (today, not current month)
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            expected_trendline_trigger = (slope * current_bar_idx) + intercept
            
            # 9. Calculate where trendline sits in Fibonacci grid
            upcoming_line_fib_pct = ((wave_peak_ceiling - expected_trendline_trigger) / total_wave_range) * 100
            
            # 10. FILTER: Only accept Fibonacci institutional zones (38.2% to 100%+)
            if upcoming_line_fib_pct < 38.2:
                return None  # Reject shallow zones
            
            # 11. Classify Fibonacci zone
            if 38.2 <= upcoming_line_fib_pct < 50.0:
                zone_tag = "38.2% (Institutional Pocket)"
            elif 50.0 <= upcoming_line_fib_pct < 61.8:
                zone_tag = "50.0% (Equilibrium Baseline)"
            elif 61.8 <= upcoming_line_fib_pct < 100.0:
                zone_tag = "61.8% (Golden Ratio Floor)"
            else:
                zone_tag = "100.0% (Full Capitulation Reset)"
            
            # 12. Calculate distance to trendline
            pct_distance_to_line = ((current_close - expected_trendline_trigger) / expected_trendline_trigger) * 100
            
            # 13. FILTER: Only accept if within ±5% of trendline (touch = entry)
            if not (-self.touch_tolerance <= pct_distance_to_line <= self.touch_tolerance):
                return None  # Stock not near trendline yet
                
            # 14. Calculate ALL Fibonacci grid prices (5 levels)
            fib_236 = wave_peak_ceiling - (total_wave_range * 0.236)
            fib_382 = wave_peak_ceiling - (total_wave_range * 0.382)
            fib_500 = wave_peak_ceiling - (total_wave_range * 0.500)
            fib_618 = wave_peak_ceiling - (total_wave_range * 0.618)
            fib_786 = wave_peak_ceiling - (total_wave_range * 0.786)
            
            # 15. Find which Fibonacci level the trendline is closest to
            fib_levels = {
                "23.6%": fib_236,
                "38.2%": fib_382, 
                "50.0%": fib_500,
                "61.8%": fib_618,
                "78.6%": fib_786
            }
            
            # Calculate distance from trendline to each Fib level
            fib_distances = {}
            for level_name, fib_price in fib_levels.items():
                distance_pct = abs((expected_trendline_trigger - fib_price) / fib_price) * 100
                fib_distances[level_name] = distance_pct
            
            # Find closest Fibonacci level to trendline
            closest_fib_level = min(fib_distances, key=fib_distances.get)
            closest_fib_distance = fib_distances[closest_fib_level]
            
            # Enhanced confluence scoring
            confluence_score = 0
            confluence_notes = []
            
            # Perfect confluence (within 1% of major Fib level)
            if closest_fib_distance <= 1.0 and closest_fib_level in ["38.2%", "50.0%", "61.8%"]:
                confluence_score = 10
                confluence_notes.append(f"PERFECT confluence with {closest_fib_level}")
            # Good confluence (within 2% of any Fib level)  
            elif closest_fib_distance <= 2.0:
                confluence_score = 7
                confluence_notes.append(f"GOOD confluence with {closest_fib_level}")
            # Moderate confluence (within 5% of major Fib level)
            elif closest_fib_distance <= 5.0 and closest_fib_level in ["38.2%", "50.0%", "61.8%"]:
                confluence_score = 5
                confluence_notes.append(f"MODERATE confluence with {closest_fib_level}")
            else:
                confluence_score = 2
                confluence_notes.append(f"Weak confluence")
            
            # Bonus for Golden Ratio (61.8%)
            if closest_fib_level == "61.8%" and closest_fib_distance <= 3.0:
                confluence_score += 3
                confluence_notes.append("GOLDEN RATIO BONUS")
            
            # 16. FUTURE PREDICTION ANALYSIS
            future_prediction = self.analyze_future_touches(df, touchbacks[0], slope, intercept, 
                                                          wave_base_origin, wave_peak_ceiling, 
                                                          total_wave_range, fib_levels)
            
            # 17. Generate position sizing and risk management
            calculated_stop_loss = expected_trendline_trigger * self.sl_multiplier
            total_shares_to_buy = int(self.capital_per_trade // expected_trendline_trigger)
            
            # 18. Alert trigger: within 1% = critical
            is_alert_active = abs(pct_distance_to_line) <= 1.0
            
            return {
                "ticker": ticker.replace(".NS", ""),
                "currentSignal": {
                    "isActive": True,
                    "currentPrice": round(current_close, 2),
                    "triggerPrice": round(expected_trendline_trigger, 2),
                    "distanceRemaining": round(abs(pct_distance_to_line), 2),
                    "fibLevelMatch": f"{round(upcoming_line_fib_pct, 2)}%",
                    "patternZone": zone_tag,
                    "confluenceScore": confluence_score,
                    "confluenceNotes": confluence_notes,
                    "notificationTrigger": bool(is_alert_active)
                },
                "futureSignal": future_prediction,
                "positionSizing": {
                    "allocatedAmount": float(self.capital_per_trade),
                    "sharesToBuy": int(total_shares_to_buy),
                    "strictStopLoss": round(calculated_stop_loss, 2),
                    "pivotTargetExit": round(wave_peak_ceiling, 2)  # Swing high after last touch
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
                },
                "trendlineDetails": {
                    "lastTouch": round(last_touch_price, 2),
                    "swingHigh": round(swing_high_after_touch, 2),
                    "slope": round(slope, 4),
                    "numTouches": num_touches
                }
            }
        except Exception as e:
            pass
        return None

    def analyze_future_touches(self, df, touch_indices, slope, intercept, wave_base, wave_peak, wave_range, fib_levels):
        """
        Analyze historical touch patterns and predict future trendline touches
        """
        try:
            # 1. Analyze historical touch intervals
            if len(touch_indices) < 3:
                return self.create_no_future_prediction("Insufficient historical touches")
            
            # Calculate time intervals between touches (in months)
            touch_intervals = []
            for i in range(1, len(touch_indices)):
                interval = touch_indices[i] - touch_indices[i-1]
                touch_intervals.append(interval)
            
            avg_interval = sum(touch_intervals) / len(touch_intervals)
            
            # 2. Analyze Fibonacci level preferences at each historical touch
            fib_preferences = {}
            historical_accuracy = []
            
            for i, touch_idx in enumerate(touch_indices[-3:]):  # Last 3 touches
                # Calculate what Fib level the trendline was at during this touch
                trendline_price_at_touch = (slope * touch_idx) + intercept
                
                # Find closest Fib level at that time
                closest_fib = None
                min_distance = float('inf')
                
                for fib_name, fib_price in fib_levels.items():
                    distance = abs((trendline_price_at_touch - fib_price) / fib_price) * 100
                    if distance < min_distance:
                        min_distance = distance
                        closest_fib = fib_name
                
                # Track preferences
                if closest_fib:
                    fib_preferences[closest_fib] = fib_preferences.get(closest_fib, 0) + 1
                    
                # Calculate accuracy (closer = better)
                accuracy = max(0, 100 - min_distance * 10)  # Convert distance to accuracy score
                historical_accuracy.append(accuracy)
            
            # 3. Predict next touch
            last_touch_idx = touch_indices[-1]
            predicted_next_touch_idx = last_touch_idx + avg_interval
            
            # Calculate predicted trendline price
            predicted_trendline_price = (slope * predicted_next_touch_idx) + intercept
            
            # 4. Determine most likely Fibonacci level
            preferred_fib_level = max(fib_preferences, key=fib_preferences.get) if fib_preferences else "61.8%"
            preferred_fib_price = fib_levels.get(preferred_fib_level, fib_levels["61.8%"])
            
            # 5. Calculate prediction confidence
            avg_accuracy = sum(historical_accuracy) / len(historical_accuracy) if historical_accuracy else 50
            interval_consistency = 100 - (max(touch_intervals) - min(touch_intervals)) * 5  # Penalty for inconsistent intervals
            confidence_score = min(95, max(30, (avg_accuracy + interval_consistency) / 2))
            
            # 6. Calculate days to predicted touch (approximate)
            current_idx = df['Price_Idx'].iloc[-1]
            months_to_touch = predicted_next_touch_idx - current_idx
            days_to_touch = int(months_to_touch * 30)  # Rough conversion
            
            # 7. Predict target date
            from datetime import datetime, timedelta
            predicted_date = datetime.now() + timedelta(days=days_to_touch)
            
            return {
                "isActive": True,
                "nextTouchDate": predicted_date.strftime('%Y-%m-%d'),
                "predictedPrice": round(predicted_trendline_price, 2),
                "predictedFibLevel": preferred_fib_level,
                "predictedFibPrice": round(preferred_fib_price, 2),
                "confidenceScore": round(confidence_score, 1),
                "daysToTouch": max(1, days_to_touch),
                "monthsToTouch": round(months_to_touch, 1),
                "historicalPattern": {
                    "avgTouchInterval": round(avg_interval, 1),
                    "fibPreferences": fib_preferences,
                    "historicalAccuracy": round(avg_accuracy, 1),
                    "touchCount": len(touch_indices)
                },
                "predictionNotes": [
                    f"Based on {len(touch_indices)} historical touches",
                    f"Prefers {preferred_fib_level} level ({fib_preferences.get(preferred_fib_level, 1)} times)",
                    f"Average interval: {avg_interval:.1f} months"
                ]
            }
            
        except Exception as e:
            return self.create_no_future_prediction(f"Prediction error: {str(e)}")
    
    def create_no_future_prediction(self, reason):
        """Create a no-prediction response"""
        return {
            "isActive": False,
            "reason": reason,
            "nextTouchDate": None,
            "predictedPrice": None,
            "confidenceScore": 0
        }
