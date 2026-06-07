"""
Fibonacci Grid and Analysis Module

This module implements Fibonacci retracement level mapping and analysis for trendline
detection and institutional buying zone identification.

Classes:
    FibonacciGrid: Store and calculate Fibonacci retracement levels
    FibonacciAnalysis: Identify touchback base and peak, analyze intersections
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
import numpy as np


@dataclass
class FibonacciGrid:
    """
    Represents a Fibonacci retracement grid with calculated levels.
    
    Attributes:
        base_price (float): The touchback base price (lowest low in recent period)
        peak_price (float): The peak price (highest high since the base)
        level_236 (float): 23.6% retracement level
        level_382 (float): 38.2% retracement level
        level_500 (float): 50.0% retracement level
        level_618 (float): 61.8% retracement level (Golden Ratio)
        level_1000 (float): 100% level (same as base_price)
    """
    base_price: float
    peak_price: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_1000: float

    def get_level_prices(self) -> Dict[str, float]:
        """
        Get all Fibonacci retracement levels as a dictionary.
        
        Returns:
            Dict[str, float]: Dictionary mapping level names to prices
                - '23.6%': level_236
                - '38.2%': level_382
                - '50.0%': level_500
                - '61.8%': level_618
                - '100%': level_1000
        """
        return {
            '23.6%': self.level_236,
            '38.2%': self.level_382,
            '50.0%': self.level_500,
            '61.8%': self.level_618,
            '100%': self.level_1000
        }

    def is_in_buying_zone(self, price: float) -> bool:
        """
        Check if price is within institutional buying zone (38.2% to 100%).
        
        Args:
            price (float): Price to check
            
        Returns:
            bool: True if price is between 38.2% level and 100% level (inclusive)
        """
        return self.level_1000 <= price <= self.level_382

    def get_closest_level(self, price: float) -> Tuple[str, float]:
        """
        Find the closest Fibonacci level to the given price.
        
        Args:
            price (float): Price to check
            
        Returns:
            Tuple[str, float]: Tuple of (level_name, distance_percentage)
        """
        levels = self.get_level_prices()
        min_distance = float('inf')
        closest_level = None

        for level_name, level_price in levels.items():
            distance_pct = abs((price - level_price) / level_price) * 100
            if distance_pct < min_distance:
                min_distance = distance_pct
                closest_level = level_name

        return closest_level, min_distance


@dataclass
class FibonacciAnalysis:
    """
    Represents Fibonacci analysis results for a trendline pattern.
    
    Attributes:
        touchback_base (float): The lowest low in recent period (start of Fibonacci grid)
        peak_price (float): The highest high since touchback base
        fibonacci_grid (FibonacciGrid): Calculated Fibonacci retracement levels
        trigger_intersection (Optional[str]): Which Fibonacci level the trendline intersects
        is_in_buying_zone (bool): Whether trigger price falls in institutional buying zone
        confluence_score (int): Score indicating Fibonacci confluence quality
    """
    touchback_base: float
    peak_price: float
    fibonacci_grid: FibonacciGrid
    trigger_intersection: Optional[str]
    is_in_buying_zone: bool
    confluence_score: int


class FibonacciAnalyzer:
    """
    Analyzes Fibonacci retracement levels and detects intersections with trendlines.
    
    This class handles:
    - Touchback base identification (lowest low in recent period)
    - Peak identification (highest high since the base)
    - Fibonacci level calculation with precise ratios
    - Intersection detection between trendline trigger price and Fibonacci zones
    - Confluence analysis combining trendline entry with Fibonacci support
    """

    def __init__(self):
        """Initialize the Fibonacci analyzer."""
        pass

    def identify_touchback_base_and_peak(
        self,
        price_series,
        lookback_months: int = 24
    ) -> Tuple[float, int, float, int]:
        """
        Identify the touchback base (lowest low) and peak (highest high) from price history.
        
        Args:
            price_series: Series of price data (typically monthly lows for base, highs for peak)
            lookback_months (int): Number of months to look back for base identification
            
        Returns:
            Tuple[float, int, float, int]: (base_price, base_idx, peak_price, peak_idx)
        """
        if len(price_series) < lookback_months:
            # Use all available data if less than lookback period
            recent_data = price_series
            recent_start_idx = 0
        else:
            recent_data = price_series[-lookback_months:]
            recent_start_idx = len(price_series) - lookback_months

        # Find base as the lowest in recent period
        base_idx_relative = np.argmin(recent_data)
        base_idx = recent_start_idx + base_idx_relative
        base_price = float(recent_data.iloc[base_idx_relative])

        # Find peak as the highest after the base
        if base_idx_relative < len(recent_data) - 1:
            data_after_base = recent_data.iloc[base_idx_relative + 1:]
            if len(data_after_base) > 0:
                peak_idx_relative = np.argmax(data_after_base)
                peak_idx = base_idx + peak_idx_relative + 1
                peak_price = float(data_after_base.iloc[peak_idx_relative])
            else:
                peak_price = float(recent_data.iloc[-1])
                peak_idx = len(price_series) - 1
        else:
            # Base is at the end, look at the entire series for peak
            peak_idx = np.argmax(price_series)
            peak_price = float(price_series.iloc[peak_idx])

        return base_price, base_idx, peak_price, peak_idx

    def calculate_fibonacci_grid(
        self,
        base_price: float,
        peak_price: float
    ) -> FibonacciGrid:
        """
        Calculate Fibonacci retracement levels between base and peak prices.
        
        Formula: level_price = peak_price - (range × fibonacci_percentage)
        
        Args:
            base_price (float): The lower price level (touchback base)
            peak_price (float): The higher price level (peak)
            
        Returns:
            FibonacciGrid: Calculated Fibonacci retracement levels
        """
        price_range = peak_price - base_price

        # Calculate each Fibonacci level
        level_236 = peak_price - (price_range * 0.236)
        level_382 = peak_price - (price_range * 0.382)
        level_500 = peak_price - (price_range * 0.500)
        level_618 = peak_price - (price_range * 0.618)
        level_1000 = base_price  # 100% retracement = base_price

        return FibonacciGrid(
            base_price=base_price,
            peak_price=peak_price,
            level_236=level_236,
            level_382=level_382,
            level_500=level_500,
            level_618=level_618,
            level_1000=level_1000
        )

    def detect_intersection(
        self,
        trigger_price: float,
        fibonacci_grid: FibonacciGrid,
        tolerance_pct: float = 2.0
    ) -> Tuple[Optional[str], bool]:
        """
        Detect if trendline trigger price intersects with any Fibonacci zone.
        
        Args:
            trigger_price (float): The trendline trigger price to check
            fibonacci_grid (FibonacciGrid): The Fibonacci grid to check against
            tolerance_pct (float): Tolerance percentage for considering an intersection
            
        Returns:
            Tuple[Optional[str], bool]: 
                - level_name: Which Fibonacci level intersects (or None if no intersection)
                - is_in_zone: Whether price is in institutional buying zone (38.2%-100%)
        """
        levels = fibonacci_grid.get_level_prices()
        closest_level, distance = fibonacci_grid.get_closest_level(trigger_price)

        # Check if within tolerance of any level
        intersects = None
        if distance <= tolerance_pct:
            intersects = closest_level

        # Check if in buying zone (38.2% to 100%)
        is_in_zone = fibonacci_grid.is_in_buying_zone(trigger_price)

        return intersects, is_in_zone

    def analyze_fibonacci_confluence(
        self,
        trigger_price: float,
        touchback_base: float,
        peak_price: float,
        price_history_lows=None,
        price_history_highs=None,
        tolerance_pct: float = 2.0
    ) -> FibonacciAnalysis:
        """
        Perform complete Fibonacci analysis including grid calculation and intersection detection.
        
        Args:
            trigger_price (float): The trendline trigger price
            touchback_base (float): The lowest low (base of Fibonacci grid)
            peak_price (float): The highest high (top of Fibonacci grid)
            price_history_lows: Optional price series for dynamic base identification
            price_history_highs: Optional price series for dynamic peak identification
            tolerance_pct (float): Tolerance for considering intersections
            
        Returns:
            FibonacciAnalysis: Complete analysis with grid and intersection data
        """
        # If price histories provided, recalculate touchback and peak
        if price_history_lows is not None:
            touchback_base, _, peak_price, _ = self.identify_touchback_base_and_peak(
                price_history_lows
            )

        # Calculate Fibonacci grid
        fib_grid = self.calculate_fibonacci_grid(touchback_base, peak_price)

        # Detect intersection
        intersects, is_in_zone = self.detect_intersection(
            trigger_price,
            fib_grid,
            tolerance_pct
        )

        # Calculate confluence score (0-10 scale)
        confluence_score = self._calculate_confluence_score(
            trigger_price,
            fib_grid,
            is_in_zone
        )

        return FibonacciAnalysis(
            touchback_base=touchback_base,
            peak_price=peak_price,
            fibonacci_grid=fib_grid,
            trigger_intersection=intersects,
            is_in_buying_zone=is_in_zone,
            confluence_score=confluence_score
        )

    def _calculate_confluence_score(
        self,
        trigger_price: float,
        fibonacci_grid: FibonacciGrid,
        is_in_zone: bool
    ) -> int:
        """
        Calculate a confluence score (0-10) based on Fibonacci alignment.
        
        Args:
            trigger_price (float): The trigger price to score
            fibonacci_grid (FibonacciGrid): The Fibonacci grid
            is_in_zone (bool): Whether price is in buying zone
            
        Returns:
            int: Confluence score (0-10)
        """
        if not is_in_zone:
            return 0

        # Find closest level and distance
        closest_level, distance = fibonacci_grid.get_closest_level(trigger_price)

        # Score based on proximity and level
        if distance <= 0.5:
            score = 10
        elif distance <= 1.0:
            score = 9
        elif distance <= 1.5:
            score = 8
        elif distance <= 2.0:
            score = 7
        else:
            score = 5

        # Bonus for Golden Ratio (61.8%)
        if closest_level == '61.8%' and distance <= 2.0:
            score = min(10, score + 1)

        return score
