#!/usr/bin/env python3
"""
Convert real trendline_screen.json to dashboard format and push to EC2
"""

import json
import boto3
import time
from datetime import datetime

def convert_to_dashboard_format(trendline_data):
    """Convert repo format to dashboard format"""
    
    dashboard_data = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "scan_summary": {
            "total_stocks_analyzed": 500,
            "stocks_meeting_criteria": len(trendline_data),
            "critical_signals": sum(1 for s in trendline_data if s.get('distanceRemaining', 0) <= 1.0),
            "watchlist_signals": sum(1 for s in trendline_data if s.get('distanceRemaining', 0) > 1.0)
        },
        "results": []
    }
    
    # Determine tab type based on distance (0-1% = radar/critical, 1-10% = trendline, >10% = volume)
    for stock in trendline_data:
        distance = stock.get('distanceRemaining', 0)
        
        # Determine tab type
        if distance <= 1.0:
            tab_type = "radar"
            status = "CRITICAL_TOUCH"
        elif distance <= 10.0:
            tab_type = "trendline"
            status = "WATCHLIST"
        else:
            tab_type = "volume"
            status = "WATCHLIST"
        
        result = {
            "ticker": stock.get('ticker', 'N/A'),
            "tab_type": tab_type,
            "current_price": stock.get('currentPrice', 0),
            "trigger_price": stock.get('triggerPrice', 0),
            "distance_percentage": distance,
            "target_exit": stock.get('positionSizing', {}).get('pivotTargetExit', 0),
            "stop_loss": stock.get('positionSizing', {}).get('strictStopLoss', 0),
            "status": status,
            "confluence_score": stock.get('confluenceScore', 0),
            "wick_touches": stock.get('wickTouches', 0),
            "pattern_zone": stock.get('patternZone', 'N/A')
        }
        
        dashboard_data["results"].append(result)
    
    # Sort by distance (closest first)
    dashboard_data["results"] = sorted(
        dashboard_data["results"],
        key=lambda x: x['distance_percentage']
    )
    
    return dashboard_data


def push_to_ec2(dashboard_data, config_path='d:\\Stock Yard\\aws_config.json'):
    """Push converted data to EC2"""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False
    
    ssm = boto3.client(
        'ssm',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    # Get instance
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['StockYard-TradingBot']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        public_ip = instance.get('PublicIpAddress', 'N/A')
        
    except Exception as e:
        print(f"✗ Error getting instance: {e}")
        return False
    
    print("\n" + "="*60)
    print("PUSHING REAL DATA TO DASHBOARD")
    print("="*60 + "\n")
    
    print(f"Instance: {instance_id}")
    print(f"IP: {public_ip}\n")
    
    # Convert to JSON
    json_str = json.dumps(dashboard_data, indent=2)
    
    print(f"⏳ Pushing {len(dashboard_data['results'])} real stock records...")
    print(f"   - Critical signals: {dashboard_data['scan_summary']['critical_signals']}")
    print(f"   - Watchlist signals: {dashboard_data['scan_summary']['watchlist_signals']}\n")
    
    # Push to EC2
    cmd = f"cat > /var/www/stockyard/trendline_screen.json << 'JSONEOF'\n{json_str}\nJSONEOF"
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [cmd]},
            TimeoutSeconds=60
        )
        
        command_id = response['Command']['CommandId']
        
        # Wait for completion
        for attempt in range(30):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print("✓ Real data pushed successfully!")
                        print(f"\n" + "="*60)
                        print("✅ DASHBOARD UPDATED WITH REAL DATA")
                        print("="*60)
                        print(f"\n🌐 Dashboard: http://{public_ip}")
                        print(f"📊 Stocks displayed: {len(dashboard_data['results'])}")
                        print(f"🔴 Critical signals: {dashboard_data['scan_summary']['critical_signals']}")
                        print(f"💡 Watchlist signals: {dashboard_data['scan_summary']['watchlist_signals']}\n")
                        return True
                    else:
                        print(f"✗ Push failed")
                        return False
            except:
                pass
        
        print("⚠️  Push timeout")
        return False
        
    except Exception as e:
        print(f"✗ Error pushing data: {e}")
        return False


if __name__ == '__main__':
    print("⏳ Reading real trendline data from repository...")
    
    try:
        with open('d:\\Stock Yard\\github_clone\\trendline_screen.json', 'r', encoding='utf-8') as f:
            trendline_data = json.load(f)
        
        print(f"✓ Loaded {len(trendline_data)} real stock records\n")
        
        # Convert format
        print("⏳ Converting to dashboard format...")
        dashboard_data = convert_to_dashboard_format(trendline_data)
        print(f"✓ Converted successfully\n")
        
        # Push to EC2
        push_to_ec2(dashboard_data)
        
    except Exception as e:
        print(f"✗ Error: {e}")
