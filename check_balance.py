#!/usr/bin/env python3
"""
Check current Angel One account balance
"""

import os
import pyotp
import logging
import json
from SmartApi import SmartConnect
from dotenv import load_dotenv

# Load credentials
load_dotenv('d:\\Stock Yard\\.env')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_balance():
    try:
        api_key = os.environ.get('ANGEL_API_KEY')
        client_id = os.environ.get('ANGEL_CLIENT_ID')
        password = os.environ.get('ANGEL_PASSWORD')
        totp_secret = os.environ.get('ANGEL_TOTP_SECRET')
        
        logger.info("Connecting to Angel One...")
        smart = SmartConnect(api_key=api_key)
        
        totp = pyotp.TOTP(totp_secret).now()
        session = smart.generateSession(client_id, password, totp)
        
        logger.info(f"Session response: {json.dumps(session, indent=2)}\n")
        
        if not isinstance(session, dict) or not session.get('status'):
            logger.error("Failed to create session")
            return
        
        logger.info("✓ Connected to Angel One\n")
        
        # Get profile with refresh token from session
        refresh_token = session.get('data', {}).get('refreshToken') if isinstance(session.get('data'), dict) else None
        
        if not refresh_token:
            logger.error("No refresh token in session response")
            return
        
        # Get margin/balance info
        margin_api = smart.getMarginApi({})
        logger.info(f"Margin API response: {json.dumps(margin_api, indent=2)}\n")
        
        if margin_api.get('status'):
            data = margin_api['data'][0] if isinstance(margin_api.get('data'), list) and len(margin_api['data']) > 0 else margin_api.get('data', {})
            
            logger.info("=" * 60)
            logger.info("💰 YOUR ACCOUNT BALANCE")
            logger.info("=" * 60)
            logger.info(f"Available Balance:  ₹{float(data.get('available', 0)):>12,.2f}")
            logger.info(f"Used Margin:        ₹{float(data.get('used', 0)):>12,.2f}")
            logger.info(f"Total Balance:      ₹{float(data.get('grossavail', 0)):>12,.2f}")
            logger.info("=" * 60)
            logger.info(f"\n✅ Available for orders: ₹{float(data.get('available', 0)):,.2f}\n")
        else:
            logger.error("Failed to get margin data")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_balance()
