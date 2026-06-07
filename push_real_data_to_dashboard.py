#!/usr/bin/env python3
"""
Push real scanner data from GitHub repo to EC2 dashboard
"""

import json
import boto3
import time
from datetime import datetime

def convert_to_dashboard_format(trendline_data):
    """Convert trendline_screen.json format to dashboard format"""
    
    results = []
    for stock in trendline_data:
        result = {
            "ticker": stock.get("ticker"),
            "tab_type": "radar" if stock.get("notificationTrigger") else "trendline",
            "current_price": stock.get("currentPrice"),
            "trigger_price": stock.get("triggerPrice"),
            "distance_percentage": stock.get("distanceRemaining"),
            "target_exit": stock.get("positionSizing", {}).get("pivotTargetExit"),
            "stop_loss": stock.get("positionSizing", {}).get("strictStopLoss"),
            "status": "CRITICAL_TOUCH" if stock.get("notificationTrigger") else "WATCHLIST",
            "confluence_score": stock.get("confluenceScore"),
            "pattern_zone": stock.get("patternZone")
        }
        results.append(result)
    
    # Count critical and watchlist
    critical = len([r for r in results if r["status"] == "CRITICAL_TOUCH"])
    watchlist = len([r for r in results if r["status"] == "WATCHLIST"])
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "scan_summary": {
            "total_stocks_analyzed": 500,
            "stocks_meeting_criteria": len(results),
            "critical_signals": critical,
            "watchlist_signals": watchlist
        },
        "results": results
    }


def push_to_ec2(dashboard_data, config_path='d:\\Stock Yard\\aws_config.json'):
    """Push converted data to EC2 dashboard"""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False
    
    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    ssm_client = boto3.client(
        'ssm',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("PUSHING REAL DATA TO EC2 DASHBOARD")
    print("="*60 + "\n")
    
    # Get instance
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['StockYard-TradingBot']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        public_ip = instance.get('PublicIpAddress', 'N/A')
        
        print(f"✓ Found instance: {instance_id}")
        print(f"  IP: {public_ip}\n")
    except Exception as e:
        print(f"✗ Error finding instance: {e}")
        return False
    
    # Push data
    json_str = json.dumps(dashboard_data, indent=2)
    cmd = f"cat > /var/www/stockyard/trendline_screen.json << 'JSONEOF'\n{json_str}\nJSONEOF"
    
    print(f"⏳ Uploading {len(dashboard_data.get('results', []))} real stock records...")
    
    try:
        response = ssm_client.send_command(
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
                result = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print(f"✓ Real data pushed successfully!\n")
                        print(f"📊 Dashboard Update:")
                        print(f"   - Total stocks: {len(dashboard_data['results'])}")
                        print(f"   - Critical signals: {dashboard_data['scan_summary']['critical_signals']}")
                        print(f"   - Watchlist: {dashboard_data['scan_summary']['watchlist_signals']}")
                        print(f"   - Timestamp: {dashboard_data['timestamp']}\n")
                        print(f"🌐 View dashboard: http://{public_ip}\n")
                        return True
                    else:
                        print(f"✗ Push failed")
                        return False
            except:
                pass
        
        print("⚠️  Push timeout")
        return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    # Load real data from GitHub repo
    try:
        with open('d:\\Stock Yard\\temp_repo\\trendline_screen.json', 'r', encoding='utf-8') as f:
            trendline_data = json.load(f)
        
        print(f"✓ Loaded {len(trendline_data)} real stocks from GitHub repo\n")
        
        # Convert format
        dashboard_data = convert_to_dashboard_format(trendline_data)
        
        # Push to EC2
        push_to_ec2(dashboard_data)
        
    except Exception as e:
        print(f"✗ Error: {e}")
