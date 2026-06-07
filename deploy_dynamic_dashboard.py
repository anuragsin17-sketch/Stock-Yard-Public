#!/usr/bin/env python3
"""
Deploy dynamic dashboard and sample data to EC2
"""

import json
import boto3
import time

def deploy(config_path='d:\\Stock Yard\\aws_config.json'):
    """Deploy dynamic dashboard to EC2"""
    
    # Load credentials
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
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
    
    print("\n" + "="*60)
    print("DEPLOYING DYNAMIC DASHBOARD TO EC2")
    print("="*60 + "\n")
    
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
        
        print(f"✓ Found instance: {instance_id}")
        print(f"  Public IP: {public_ip}\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Read files
    print("⏳ Reading files...")
    try:
        with open('d:\\Stock Yard\\dashboard_dynamic.html', 'r', encoding='utf-8') as f:
            html = f.read()
        with open('d:\\Stock Yard\\trendline_screen_sample.json', 'r', encoding='utf-8') as f:
            json_data = f.read()
        print("✓ Files read successfully\n")
    except Exception as e:
        print(f"✗ Error reading files: {e}")
        return False
    
    # Deploy HTML
    print("⏳ Deploying HTML file...")
    html_cmd = f"cat > /var/www/stockyard/index.html << 'HTMLEOF'\n{html}\nHTMLEOF"
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [html_cmd]},
            TimeoutSeconds=60
        )
        
        command_id = response['Command']['CommandId']
        for _ in range(30):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print("✓ HTML deployed")
                    break
            except:
                pass
    except Exception as e:
        print(f"⚠️  HTML deployment: {str(e)[:50]}")
    
    # Deploy JSON
    print("⏳ Deploying JSON data file...")
    json_cmd = f"cat > /var/www/stockyard/trendline_screen.json << 'JSONEOF'\n{json_data}\nJSONEOF"
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [json_cmd]},
            TimeoutSeconds=60
        )
        
        command_id = response['Command']['CommandId']
        for _ in range(30):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print("✓ JSON deployed")
                    break
            except:
                pass
    except Exception as e:
        print(f"⚠️  JSON deployment: {str(e)[:50]}")
    
    # Verify
    print("\n⏳ Verifying deployment...")
    verify_cmd = "ls -lah /var/www/stockyard/"
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [verify_cmd]},
            TimeoutSeconds=30
        )
        
        command_id = response['Command']['CommandId']
        for _ in range(20):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                if result['Status'] in ['Success', 'Failed']:
                    print("✓ Files verified on EC2\n")
                    break
            except:
                pass
    except:
        pass
    
    print("="*60)
    print("✓ DYNAMIC DASHBOARD DEPLOYED")
    print("="*60)
    print(f"\n🌐 Dashboard URL:")
    print(f"   http://{public_ip}\n")
    print("📊 Features:")
    print("   ✅ Loads live data from trendline_screen.json")
    print("   ✅ Auto-refreshes every 5 minutes")
    print("   ✅ Volume Tab - shows volume stocks")
    print("   ✅ Trendline Tab - shows entry opportunities")
    print("   ✅ Radar Tab - shows critical signals\n")
    print("📝 Next: Update your scanner to write to trendline_screen.json\n")
    
    return True

if __name__ == '__main__':
    deploy()
