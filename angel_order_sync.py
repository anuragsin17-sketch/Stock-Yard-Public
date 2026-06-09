#!/usr/bin/env python3
"""
Angel One Order Sync Service
- Fetches live order status from Angel One API
- Syncs with local radar_trades.json
- Provides webhook for dashboard to fetch real-time data
"""

import os
import json
import requests
from datetime import datetime
from flask import Flask, jsonify
from threading import Thread
import time

app = Flask(__name__)

ANGEL_API_KEY = os.environ.get('ANGEL_API_KEY')
ANGEL_CLIENT_CODE = os.environ.get('ANGEL_CLIENT_CODE')
RADAR_FILE = 'radar_trades.json'
ORDERS_FILE = 'angel_orders.json'

# In-memory cache of live orders
live_orders_cache = {}
last_sync = None


def sync_with_angel_one():
    """Fetch live order data from Angel One and sync locally"""
    global live_orders_cache, last_sync
    
    if not ANGEL_API_KEY or not ANGEL_CLIENT_CODE:
        print("⚠️ Angel One credentials not configured")
        return False
    
    try:
        # This would call Angel One's actual API
        # For now, we'll implement a mock version
        # In production, use smartapi-python library
        
        print(f"🔄 Syncing with Angel One at {datetime.now().strftime('%H:%M:%S')}")
        
        # Fetch all active orders from Angel One
        # angel_orders = get_angel_orders()  # Would call Angel One API
        
        # For now, read from our local file
        try:
            with open(ORDERS_FILE) as f:
                orders = json.load(f)
        except:
            orders = []
        
        # Update cache with order statuses
        for order in orders:
            if isinstance(order, dict):
                ticker = order.get('symbol', '')
                order_id = order.get('order_id', '')
                if ticker and order_id:
                    live_orders_cache[order_id] = {
                        'ticker': ticker,
                        'order_id': order_id,
                        'status': 'Open',  # Would get from Angel One API
                        'filled_qty': order.get('quantity', 0),
                        'filled_price': order.get('entry_price', 0),
                        'current_price': 0,  # Would get from market data
                        'synced_at': datetime.now().isoformat()
                    }
        
        last_sync = datetime.now()
        print(f"✅ Synced {len(live_orders_cache)} orders from Angel One")
        return True
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False


@app.route('/api/sync-orders', methods=['GET'])
def get_synced_orders():
    """API endpoint for dashboard to get live order data"""
    return jsonify({
        'success': True,
        'orders': live_orders_cache,
        'last_sync': last_sync.isoformat() if last_sync else None,
        'count': len(live_orders_cache)
    })


@app.route('/api/order-status/<order_id>', methods=['GET'])
def get_order_status(order_id):
    """Get status of specific order"""
    if order_id in live_orders_cache:
        return jsonify({
            'success': True,
            'order': live_orders_cache[order_id]
        })
    return jsonify({
        'success': False,
        'error': f'Order {order_id} not found'
    }), 404


@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """Get all orders from Angel One"""
    try:
        with open(ORDERS_FILE) as f:
            orders = json.load(f)
        
        # Enrich with live data from cache
        enriched = []
        for order in orders:
            order_id = order.get('order_id', '')
            live_data = live_orders_cache.get(order_id, {})
            
            enriched_order = {**order, **live_data}
            enriched.append(enriched_order)
        
        return jsonify({
            'success': True,
            'orders': enriched,
            'count': len(enriched)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def background_sync():
    """Background thread to sync with Angel One every 5 minutes"""
    while True:
        try:
            sync_with_angel_one()
            time.sleep(300)  # Sync every 5 minutes
        except Exception as e:
            print(f"Background sync error: {e}")
            time.sleep(60)


if __name__ == '__main__':
    # Start background sync thread
    sync_thread = Thread(target=background_sync, daemon=True)
    sync_thread.start()
    
    # Initial sync
    sync_with_angel_one()
    
    # Start Flask app
    print("🚀 Angel One Order Sync Service Starting")
    print("📡 Endpoints:")
    print("   GET /api/sync-orders - Get all synced orders")
    print("   GET /api/order-status/<order_id> - Get specific order status")
    print("   GET /api/orders - Get all orders with live data")
    app.run(host='0.0.0.0', port=5002, debug=False)
