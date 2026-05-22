#!/usr/bin/env python3
"""
Position Tracker - Automatic Position Management
Tracks when stocks hit trigger prices and targets
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PositionTracker:
    def __init__(self, positions_file='positions.json'):
        self.positions_file = positions_file
        self.positions = self.load_positions()
    
    def load_positions(self) -> Dict:
        """Load existing positions from file"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading positions: {e}")
                return {'open_positions': [], 'closed_positions': []}
        return {'open_positions': [], 'closed_positions': []}
    
    def save_positions(self):
        """Save positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
            logger.info(f"Positions saved: {len(self.positions['open_positions'])} open, {len(self.positions['closed_positions'])} closed")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def check_and_update_positions(self, screening_results: Dict):
        """
        Check all stocks across all categories and update positions
        - If current price hits trigger price (within 1%), mark as Position Taken
        - If current price hits target (20% from entry), mark as Position Closed
        """
        all_stocks = []
        
        # Collect all stocks with trigger prices from all categories
        for stock in screening_results.get('golden_stocks', []):
            if stock.get('trendline_price'):
                all_stocks.append({
                    'symbol': stock['symbol'],
                    'company_name': stock['company_name'],
                    'category': 'Golden Stock',
                    'trigger_price': stock['trendline_price'],
                    'current_price': stock['current_price'],
                    'timeframe': stock.get('primary_timeframe', 'Weekly')
                })
        
        for stock in screening_results.get('volume_breakout_stocks', []):
            if stock.get('radar_trigger_price'):
                all_stocks.append({
                    'symbol': stock['symbol'],
                    'company_name': stock['company_name'],
                    'category': 'Volume Breakout',
                    'trigger_price': stock['radar_trigger_price'],
                    'current_price': stock['current_price'],
                    'breakout_date': stock.get('breakout_date')
                })
        
        for stock in screening_results.get('w_pattern_stocks', []):
            if stock.get('radar_trigger_price'):
                all_stocks.append({
                    'symbol': stock['symbol'],
                    'company_name': stock['company_name'],
                    'category': 'W-Pattern',
                    'trigger_price': stock['radar_trigger_price'],
                    'current_price': stock['current_price'],
                    'neckline_price': stock.get('neckline_peak_price')
                })
        
        for stock in screening_results.get('elliott_wave_stocks', []):
            if stock.get('golden_pocket_low'):
                all_stocks.append({
                    'symbol': stock['symbol'],
                    'company_name': stock['company_name'],
                    'category': 'Elliott Wave',
                    'trigger_price': stock['golden_pocket_low'],
                    'current_price': stock['current_price'],
                    'golden_pocket_high': stock.get('golden_pocket_high')
                })
        
        # Process each stock
        for stock in all_stocks:
            self._process_stock(stock)
        
        # Save updated positions
        self.save_positions()
    
    def _process_stock(self, stock: Dict):
        """Process individual stock for position tracking with improved logic"""
        symbol = stock['symbol']
        current_price = stock['current_price']
        trigger_price = stock['trigger_price']
        
        # Check if position already exists
        existing_open = self._find_position(symbol, self.positions['open_positions'])
        existing_closed = self._find_position(symbol, self.positions['closed_positions'])
        
        # Skip if already closed
        if existing_closed:
            return
        
        # Calculate distance to trigger price
        distance_to_trigger = abs(current_price - trigger_price) / trigger_price * 100
        
        # Check if we should open a position (within 1% of trigger price)
        if not existing_open and distance_to_trigger <= 1.0:
            self._open_position(stock)
        
        # Check if we should close an existing position
        elif existing_open:
            entry_price = existing_open['entry_price']
            target_price = entry_price * 1.20  # 20% target
            stoploss_price = entry_price * 0.92  # 8% stop loss (widened from 5%)
            
            # Calculate current gain
            current_gain_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Trailing stop loss: If position is +10%, move stop to breakeven
            if current_gain_percent >= 10:
                stoploss_price = entry_price  # Breakeven stop
            
            # Check for target hit (20%)
            if current_price >= target_price:
                self._close_position(existing_open, current_price, target_price, 'Target Hit (20%)')
            
            # Check for stop loss hit (8% or breakeven)
            elif current_price <= stoploss_price:
                reason = 'Stop Loss Hit (8%)' if stoploss_price < entry_price else 'Breakeven Stop Hit'
                self._close_position(existing_open, current_price, stoploss_price, reason)
            else:
                # Update current price for open position
                existing_open['current_price'] = current_price
                existing_open['current_gain_percent'] = round(current_gain_percent, 2)
                existing_open['last_updated'] = datetime.now().isoformat()
                existing_open['stoploss_price'] = round(stoploss_price, 2)  # Update trailing stop
    
    def _find_position(self, symbol: str, positions_list: List) -> Dict:
        """Find position by symbol"""
        for pos in positions_list:
            if pos['symbol'] == symbol:
                return pos
        return None
    
    def _open_position(self, stock: Dict):
        """Open a new position"""
        entry_price = stock['current_price']
        target_price = entry_price * 1.20  # 20% target
        stoploss_price = entry_price * 0.92  # 8% stop loss (improved from 5%)
        
        position = {
            'symbol': stock['symbol'],
            'company_name': stock['company_name'],
            'category': stock['category'],
            'entry_price': round(entry_price, 2),
            'target_price': round(target_price, 2),
            'stoploss_price': round(stoploss_price, 2),
            'current_price': round(entry_price, 2),
            'current_gain_percent': 0.0,
            'entry_date': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'status': 'Position Taken'
        }
        
        # Add category-specific data
        if 'timeframe' in stock:
            position['timeframe'] = stock['timeframe']
        if 'breakout_date' in stock:
            position['breakout_date'] = stock['breakout_date']
        if 'neckline_price' in stock:
            position['neckline_price'] = stock['neckline_price']
        
        self.positions['open_positions'].append(position)
        logger.info(f"✅ Position Taken: {stock['symbol']} at ₹{entry_price:.2f} | Target: ₹{target_price:.2f} | Stop: ₹{stoploss_price:.2f}")
    
    def _close_position(self, position: Dict, exit_price: float, target_or_stop: float, reason: str):
        """Close an existing position"""
        entry_price = position['entry_price']
        gain_percent = ((exit_price - entry_price) / entry_price) * 100
        
        # Update position with exit details
        position['exit_price'] = round(exit_price, 2)
        position['exit_date'] = datetime.now().isoformat()
        position['gain_percent'] = round(gain_percent, 2)
        position['status'] = 'Position Closed'
        position['exit_reason'] = reason
        
        # Move from open to closed
        self.positions['open_positions'].remove(position)
        self.positions['closed_positions'].append(position)
        
        emoji = "🎯" if gain_percent > 0 else "🛑"
        logger.info(f"{emoji} Position Closed: {position['symbol']} | Entry: ₹{entry_price:.2f} | Exit: ₹{exit_price:.2f} | Gain: {gain_percent:+.2f}% | {reason}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        open_positions = self.positions['open_positions']
        closed_positions = self.positions['closed_positions']
        
        # Calculate average gain for closed positions
        avg_gain = 0
        if closed_positions:
            total_gain = sum(pos['gain_percent'] for pos in closed_positions)
            avg_gain = total_gain / len(closed_positions)
        
        # Calculate total unrealized gain for open positions
        total_unrealized = sum(pos.get('current_gain_percent', 0) for pos in open_positions)
        
        return {
            'total_open': len(open_positions),
            'total_closed': len(closed_positions),
            'avg_gain_closed': round(avg_gain, 2),
            'total_unrealized_gain': round(total_unrealized, 2),
            'open_positions': open_positions,
            'closed_positions': closed_positions
        }
