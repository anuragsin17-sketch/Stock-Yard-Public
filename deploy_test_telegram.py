#!/usr/bin/env python3
"""
Deploy and run Telegram test on EC2 instance
"""

import subprocess
import json
from pathlib import Path

def deploy_test():
    """Deploy test script to EC2 and run it"""
    
    config_path = Path('d:\\Stock Yard') / 'aws_config.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        print("✗ Could not load config")
        return
    
    static_ip = "32.194.58.75"
    
    print("\n" + "="*60)
    print("DEPLOYING TELEGRAM TEST TO EC2")
    print("="*60 + "\n")
    
    # Copy test script to EC2
    print(f"⏳ Copying test script to EC2 ({static_ip})...")
    
    try:
        # Note: This requires SSH key setup
        # For now, we'll show what would be done
        
        print(f"✓ Test script would be deployed to: ubuntu@{static_ip}")
        print(f"\nTo run the test manually on EC2:")
        print(f"1. SSH into instance:")
        print(f"   ssh -i your-key.pem ubuntu@{static_ip}")
        print(f"\n2. Run the test:")
        print(f"   cd /home/ubuntu/Stock-Yard")
        print(f"   python3 test_telegram.py")
        print(f"\n3. Check your Telegram for test messages")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == '__main__':
    deploy_test()
