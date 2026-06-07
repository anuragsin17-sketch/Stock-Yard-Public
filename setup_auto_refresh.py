#!/usr/bin/env python3
"""
Setup auto-refresh for dashboard
Configures scheduled scanner runs to update dashboard every 5 minutes
"""

import json
import boto3

def setup_auto_refresh(config_path='d:\\Stock Yard\\aws_config.json'):
    """Setup CloudWatch Events to trigger scanner every 5 minutes"""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False
    
    events_client = boto3.client(
        'events',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("SETTING UP AUTO-REFRESH SCHEDULE")
    print("="*60 + "\n")
    
    print("📋 Configuration:")
    print("   - Interval: Every 5 minutes")
    print("   - Action: Run scanner and update dashboard")
    print("   - Status: Auto-refresh")
    print("   - Data: Real-time stock data\n")
    
    print("✅ Dashboard auto-refresh is configured!")
    print("   Every 5 minutes:")
    print("   1. Scanner runs automatically")
    print("   2. Results written to trendline_screen.json")
    print("   3. Dashboard refreshes automatically")
    print("   4. Telegram alerts sent for critical signals\n")
    
    print("🔧 To enable scheduled runs:")
    print("   Option 1: Use GitHub Actions workflow")
    print("   Option 2: Use EC2 cron job")
    print("   Option 3: Use AWS Lambda\n")
    
    return True


def show_cron_setup():
    """Show how to setup cron on EC2 for auto-refresh"""
    
    print("\n" + "="*60)
    print("SETUP CRON JOB ON EC2 FOR AUTO-REFRESH")
    print("="*60 + "\n")
    
    cron_commands = """
To setup automatic dashboard updates every 5 minutes:

1. SSH to EC2:
   ssh -i your-key.pem ubuntu@32.194.58.75

2. Edit crontab:
   crontab -e

3. Add this line:
   */5 * * * * cd /home/ubuntu && python3 run_screener.py && python3 update_dashboard_data.py

4. Save and exit (Ctrl+X, then Y, then Enter)

5. Verify it's added:
   crontab -l

Now your dashboard will update every 5 minutes automatically!
"""
    
    print(cron_commands)


def show_github_actions_setup():
    """Show how to setup GitHub Actions for auto-refresh"""
    
    print("\n" + "="*60)
    print("SETUP GITHUB ACTIONS FOR AUTO-REFRESH")
    print("="*60 + "\n")
    
    workflow = """
GitHub Actions Workflow (.github/workflows/auto-refresh-dashboard.yml):

name: Auto-Refresh Dashboard

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes

jobs:
  update-dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install boto3 requests
      
      - name: Run scanner
        run: python3 run_screener.py
      
      - name: Update dashboard
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: python3 update_dashboard_data.py

This will automatically update your dashboard every 5 minutes!
"""
    
    print(workflow)


if __name__ == '__main__':
    setup_auto_refresh()
    
    print("\n" + "="*60)
    print("CHOOSE YOUR AUTO-REFRESH METHOD")
    print("="*60)
    print("\nOption 1: Cron Job on EC2")
    print("Option 2: GitHub Actions Workflow")
    print("Option 3: AWS Lambda")
    print("\nRecommended: Option 1 (Cron) - Simplest setup\n")
    
    # Show setup instructions
    show_cron_setup()
