import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

class MacroInstitutionalEngine:
    def __init__(self, position_size=50000.0, sl_pct=8.0, touch_tolerance=2.0):
        """
        Initializes your precise pattern scanning and risk allocation matrices.
        
        Args:
            position_size: Capital allocated per trade (default: ₹50,000)
            sl_pct: Stop loss percentage below trendline (default: 8%)
            touch_tolerance: Percentage tolerance for trendline touch detection (default: ±2%)
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
            
            # 13. FILTER: Only accept if within ±2% of trendline (touch = entry)
            if not (-self.touch_tolerance <= pct_distance_to_line <= self.touch_tolerance):
                return None  # Stock not near trendline yet
                
            # 14. Calculate Fibonacci grid prices
            fib_236 = wave_peak_ceiling - (total_wave_range * 0.236)
            fib_382 = wave_peak_ceiling - (total_wave_range * 0.382)
            fib_500 = wave_peak_ceiling - (total_wave_range * 0.500)
            fib_618 = wave_peak_ceiling - (total_wave_range * 0.618)
            
            # 15. Generate position sizing and risk management
            calculated_stop_loss = expected_trendline_trigger * self.sl_multiplier
            total_shares_to_buy = int(self.capital_per_trade // expected_trendline_trigger)
            
            # 16. Alert trigger: within 1% = critical
            is_alert_active = abs(pct_distance_to_line) <= 1.0
            
            return {
                "ticker": ticker.replace(".NS", ""),
                "currentPrice": round(current_close, 2),
                "triggerPrice": round(expected_trendline_trigger, 2),
                "distanceRemaining": round(abs(pct_distance_to_line), 2),
                "fibLevelMatch": f"{round(upcoming_line_fib_pct, 2)}%",
                "patternZone": zone_tag,
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
                    "level_1000": round(wave_base_origin, 2)
                },
                "trendlineDetails": {
                    "lastTouch": round(last_touch_price, 2),
                    "swingHigh": round(swing_high_after_touch, 2),
                    "slope": round(slope, 4),
                    "numTouches": num_touches
                },
                "notificationTrigger": bool(is_alert_active)
            }
        except Exception as e:
            pass
        return None
