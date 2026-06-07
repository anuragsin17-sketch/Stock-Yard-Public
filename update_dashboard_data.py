#!/usr/bin/env python3
"""
Update dashboard data on EC2
Writes stock scan results to trendline_screen.json on EC2 instance
This script should be called by your scanner after generating results
"""

import json
import boto3
from datetime import datetime
import time

class DashboardUpdater:
    def __init__(self, config_path='d:\\Stock Yard\\aws_config.json'):
        """Initialize with AWS credentials"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"✗ Error loading config: {e}")
            raise
        
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=self.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=self.config['AWS_SECRET_ACCESS_KEY'],
            region_name=self.config['AWS_REGION']
        )
        
        self.ssm_client = boto3.client(
            'ssm',
            aws_access_key_id=self.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=self.config['AWS_SECRET_ACCESS_KEY'],
            region_name=self.config['AWS_REGION']
        )
    
    def get_instance_info(self):
        """Get EC2 instance details"""
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': ['StockYard-TradingBot']},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            if not response['Reservations']:
                raise Exception("No running instances found")
            
            instance = response['Reservations'][0]['Instances'][0]
            return {
                'instance_id': instance['InstanceId'],
                'public_ip': instance.get('PublicIpAddress'),
                'private_ip': instance.get('PrivateIpAddress')
            }
        except Exception as e:
            print(f"✗ Error getting instance info: {e}")
            raise
    
    def update_dashboard(self, stock_data):
        """
        Update dashboard JSON on EC2
        
        Args:
            stock_data: Dictionary with structure:
            {
                "results": [
                    {
                        "ticker": "RELIANCE",
                        "tab_type": "volume|trendline|radar",
                        "current_price": 2456.75,
                        "trigger_price": 2445.20,
                        "distance_percentage": 0.47,
                        "target_exit": 2934.24,
                        "stop_loss": 2249.58,
                        "status": "WATCHLIST|CRITICAL_TOUCH",
                        ...
                    }
                ],
                "scan_summary": {
                    "total_stocks_analyzed": 500,
                    "stocks_meeting_criteria": 12,
                    "critical_signals": 3,
                    "watchlist_signals": 9
                }
            }
        """
        
        try:
            instance_info = self.get_instance_info()
            instance_id = instance_info['instance_id']
            
            print("\n" + "="*60)
            print("UPDATING DASHBOARD ON EC2")
            print("="*60)
            print(f"Instance: {instance_id}")
            print(f"IP: {instance_info['public_ip']}\n")
            
            # Add timestamp
            stock_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            
            # Convert to JSON
            json_str = json.dumps(stock_data, indent=2)
            
            print(f"⏳ Uploading {len(stock_data.get('results', []))} stock records...")
            
            # Write to EC2 via SSM
            cmd = f"cat > /var/www/stockyard/trendline_screen.json << 'JSONEOF'\n{json_str}\nJSONEOF"
            
            response = self.ssm_client.send_command(
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
                    result = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id
                    )
                    
                    if result['Status'] in ['Success', 'Failed']:
                        if result['Status'] == 'Success':
                            print(f"✓ Dashboard updated successfully")
                            print(f"  - Total records: {len(stock_data.get('results', []))}")
                            print(f"  - Timestamp: {stock_data['timestamp']}")
                            print(f"\n🌐 View at: http://{instance_info['public_ip']}\n")
                            return True
                        else:
                            print(f"✗ Update failed")
                            return False
                except:
                    pass
            
            print("⚠️  Update timeout")
            return False
            
        except Exception as e:
            print(f"✗ Error updating dashboard: {e}")
            return False


def update_from_scanner_results(scanner_results_path, config_path='d:\\Stock Yard\\aws_config.json'):
    """
    Convenience function to update dashboard from scanner results file
    
    Args:
        scanner_results_path: Path to JSON file with scanner results
        config_path: Path to AWS config file
    """
    try:
        with open(scanner_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updater = DashboardUpdater(config_path)
        return updater.update_dashboard(data)
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    # Example usage
    sample_data = {
        "scan_summary": {
            "total_stocks_analyzed": 500,
            "stocks_meeting_criteria": 7,
            "critical_signals": 3,
            "watchlist_signals": 4
        },
        "results": [
            {
                "ticker": "RELIANCE",
                "tab_type": "volume",
                "current_price": 2456.75,
                "trigger_price": 2445.20,
                "distance_percentage": 0.47,
                "target_exit": 2934.24,
                "stop_loss": 2249.58,
                "status": "WATCHLIST",
                "volume": "50M"
            },
            {
                "ticker": "TCS",
                "tab_type": "volume",
                "current_price": 3500.00,
                "trigger_price": 3485.50,
                "distance_percentage": 0.42,
                "target_exit": 4182.00,
                "stop_loss": 3206.26,
                "status": "WATCHLIST",
                "volume": "35M"
            },
            {
                "ticker": "WIPRO",
                "tab_type": "trendline",
                "current_price": 400.50,
                "trigger_price": 385.00,
                "distance_percentage": 4.02,
                "target_exit": 480.00,
                "stop_loss": 354.20,
                "status": "WATCHLIST"
            },
            {
                "ticker": "HCLTECH",
                "tab_type": "trendline",
                "current_price": 1250.00,
                "trigger_price": 1200.00,
                "distance_percentage": 4.17,
                "target_exit": 1530.00,
                "stop_loss": 1104.00,
                "status": "WATCHLIST"
            },
            {
                "ticker": "BAJAJFINSV",
                "tab_type": "radar",
                "current_price": 1520.00,
                "trigger_price": 1500.00,
                "distance_percentage": 1.33,
                "target_exit": 1800.00,
                "stop_loss": 1380.00,
                "status": "CRITICAL_TOUCH",
                "confluence_score": 9
            },
            {
                "ticker": "INFY",
                "tab_type": "radar",
                "current_price": 1650.00,
                "trigger_price": 1640.00,
                "distance_percentage": 0.61,
                "target_exit": 1968.00,
                "stop_loss": 1508.80,
                "status": "CRITICAL_TOUCH",
                "confluence_score": 8
            },
            {
                "ticker": "LT",
                "tab_type": "radar",
                "current_price": 2100.00,
                "trigger_price": 2090.00,
                "distance_percentage": 0.48,
                "target_exit": 2508.00,
                "stop_loss": 1922.80,
                "status": "CRITICAL_TOUCH",
                "confluence_score": 9
            }
        ]
    }
    
    updater = DashboardUpdater()
    updater.update_dashboard(sample_data)
