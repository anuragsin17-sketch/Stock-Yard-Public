import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

class MacroInstitutionalEngine:
    def __init__(self, position_size=50000.0, sl_pct=8.0, touch_tolerance=2.0):
        """
        Trendline engine with all learned improvements:
        - Wick-based touch detection (candle lows = wicks count as touches)
        - Adaptive order parameter (handles all sector cycle lengths)
        - ±2% entry discipline (strict, not ±5% or ±10%)
        - Fibonacci confluence within 2% only
        - Dynamic stop loss (8% below current trendline, moves up monthly)
        - Minimum 3 wick touches required
        """
        self.capital_per_trade = float(position_size)
        self.sl_multiplier = 1.0 - (float(sl_pct) / 100.0)
        self.touch_tolerance = float(touch_tolerance)  # ±2% entry

    def get_sector_order(self, ticker):
        """Sector-specific order parameter with adaptive fallback"""
        banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
                   'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
        return 6 if any(b in ticker.upper() for b in banking) else 10

    def find_trendline_anchors(self, low_prices, df, ticker):
        """
        Find major anchor bottoms with adaptive order.
        Tries progressively smaller orders to handle all cycle lengths.
        """
        base_order = self.get_sector_order(ticker)
        touchbacks = argrelextrema(low_prices, np.less, order=base_order)

        # Adaptive fallback for long-cycle stocks (e.g. MARUTI needs order=5)
        for fallback_order in [8, 6, 5]:
            if len(touchbacks[0]) >= 2:
                break
            touchbacks = argrelextrema(low_prices, np.less, order=fallback_order)

        return touchbacks

    def count_wick_touches(self, df, low_prices, slope, intercept, tolerance=8.0):
        """
        Count wick touches - candle LOW (wick) within tolerance% of trendline.
        Relaxed to 8% to catch more valid touches across different stock volatilities.
        """
        wick_touches = []
        for i in range(len(df)):
            month_idx = df['Price_Idx'].iloc[i]
            trendline_at_month = (slope * month_idx) + intercept
            candle_low = low_prices[i]  # Wick low

            distance_pct = abs((candle_low - trendline_at_month) / trendline_at_month) * 100

            if distance_pct <= tolerance:
                wick_touches.append({
                    'date': df.index[i].strftime('%Y-%m-%d'),
                    'price': round(float(candle_low), 2),
                    'trendline_price': round(float(trendline_at_month), 2),
                    'distance_pct': round(distance_pct, 2),
                    'month_idx': int(month_idx)
                })
        return wick_touches

    def calculate_fib_confluence(self, last_touch_price, swing_high, trigger_price):
        """
        Fibonacci confluence scoring.
        RULE: Only count if trendline is within 2% of Fib level.
        If no Fib within 2%, trendline touch alone is valid (score=6).
        """
        try:
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return 6, "No Fib range", None

            fib_levels = {
                '23.6%': swing_high - (fib_range * 0.236),
                '38.2%': swing_high - (fib_range * 0.382),
                '50.0%': swing_high - (fib_range * 0.500),
                '61.8%': swing_high - (fib_range * 0.618),
                '78.6%': swing_high - (fib_range * 0.786)
            }

            min_distance = float('inf')
            closest_level = None
            for level_name, fib_price in fib_levels.items():
                dist = abs((trigger_price - fib_price) / fib_price) * 100
                if dist < min_distance:
                    min_distance = dist
                    closest_level = level_name

            # Only count Fib confluence if within 2%
            if min_distance <= 2.0:
                if min_distance <= 0.5:
                    score = 10
                elif min_distance <= 1.0:
                    score = 9
                else:
                    score = 8
                # Golden Ratio bonus
                if closest_level == '61.8%':
                    score = min(10, score + 1)
                note = f"Fib confluence: {closest_level} ({min_distance:.1f}% away)"
            else:
                score = 6  # Trendline touch alone is valid
                note = f"No Fib within 2% (closest: {closest_level} at {min_distance:.1f}%)"

            return score, note, fib_levels

        except Exception:
            return 6, "Fib calculation error", None

    def find_swing_high_after_touch(self, df, last_touch_idx):
        """Find swing high after last trendline touch"""
        data_after_touch = df.iloc[last_touch_idx:]
        if len(data_after_touch) < 3:
            return df['High'].max().item()
        highs = data_after_touch['High'].values
        maxima_indices = argrelextrema(highs, np.greater, order=3)[0]
        if len(maxima_indices) > 0:
            return data_after_touch['High'].iloc[maxima_indices].max().item()
        return data_after_touch['High'].max().item()

    def process_ticker_geometry(self, ticker: str):
        """
        Main analysis with all learned improvements:
        1. Wick-based touch detection
        2. Adaptive order parameter
        3. ±2% entry discipline
        4. Fibonacci confluence within 2% only
        5. Dynamic stop loss (8% below current trendline)
        6. Minimum 3 wick touches
        7. Entry AT trendline price (not market price)
        """
        try:
            # 1. Fetch 8-year monthly data (as learned)
            df = yf.download(ticker, period="8y", interval="1mo",
                             auto_adjust=True, progress=False)
            if df.empty or len(df) < 24:
                return None

            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()

            # 2. Find anchor bottoms with adaptive order
            touchbacks = self.find_trendline_anchors(low_prices, df, ticker)
            if len(touchbacks[0]) < 2:
                return None

            # 3. Fit trendline using last 3 anchors
            num_anchors = min(3, len(touchbacks[0]))
            anchor_indices = touchbacks[0][-num_anchors:]
            x_anchors = [df['Price_Idx'].iloc[i] for i in anchor_indices]
            y_anchors = [low_prices[i] for i in anchor_indices]
            slope, intercept = np.polyfit(x_anchors, y_anchors, 1)

            # 4. Must be ascending
            if slope <= 0:
                return None

            # 5. Count WICK touches (KEY FIX - wicks count!)
            wick_touches = self.count_wick_touches(df, low_prices, slope, intercept, tolerance=5.0)

            # 6. Minimum 3 wick touches required
            if len(wick_touches) < 3:
                return None

            # 7. Current trigger price (imaginary vertical line method)
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            trigger_price = (slope * current_bar_idx) + intercept

            # 8. Distance from current price to trendline
            pct_distance = ((current_close - trigger_price) / trigger_price) * 100

            # 9. Entry filter: ±2% only (strict discipline)
            if abs(pct_distance) > self.touch_tolerance:
                return None

            # 10. Fibonacci confluence (within 2% only)
            last_touch_idx = anchor_indices[-1]
            last_touch_price = float(low_prices[last_touch_idx])
            swing_high = self.find_swing_high_after_touch(df, last_touch_idx)

            confluence_score, confluence_note, fib_levels = self.calculate_fib_confluence(
                last_touch_price, swing_high, trigger_price
            )

            # 11. Dynamic stop loss (8% below CURRENT trendline - moves up monthly)
            dynamic_stop_loss = trigger_price * self.sl_multiplier

            # 12. Target (20% above trendline entry)
            target_price = trigger_price * 1.20

            # 13. Signal status
            if abs(pct_distance) <= 1.0:
                signal_status = "CRITICAL_TOUCH"
            else:
                signal_status = "WATCHLIST"

            # 14. Position sizing
            shares = int(self.capital_per_trade // trigger_price)

            # 15. Fib grid for display
            fib_grid = {}
            if fib_levels:
                fib_grid = {k: round(v, 2) for k, v in fib_levels.items()}

            return {
                "ticker": ticker.replace(".NS", ""),
                "currentSignal": {
                    "isActive": True,
                    "currentPrice": round(current_close, 2),
                    "triggerPrice": round(trigger_price, 2),  # Entry AT trendline
                    "distanceRemaining": round(abs(pct_distance), 2),
                    "signalStatus": signal_status,
                    "confluenceScore": confluence_score,
                    "confluenceNote": confluence_note,
                    "notificationTrigger": signal_status == "CRITICAL_TOUCH"
                },
                "positionSizing": {
                    "allocatedAmount": float(self.capital_per_trade),
                    "sharesToBuy": shares,
                    "entryPrice": round(trigger_price, 2),       # AT trendline
                    "dynamicStopLoss": round(dynamic_stop_loss, 2),  # 8% below trendline
                    "targetExit": round(target_price, 2),         # 20% above trendline
                    "stopNote": "Dynamic: updates monthly as trendline rises"
                },
                "trendlineDetails": {
                    "wickTouches": len(wick_touches),
                    "lastWickTouch": wick_touches[-1] if wick_touches else None,
                    "slope": round(slope, 4),
                    "numAnchors": num_anchors,
                    "monthlyGrowthRate": round(slope, 2)
                },
                "fibGrid": fib_grid
            }

        except Exception:
            pass
        return None
