#!/usr/bin/env python3
"""
AWS EC2 Deployment Script for Stock Yard Trading Bot
Reads credentials from aws_config.json and deploys bot to AWS
"""

import json
import boto3
import time
import sys
from pathlib import Path

def load_config(config_path):
    """Load AWS and deployment config from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded config from {config_path}")
        
        # If region is ap-south-1, suggest switching to us-east-1 for free tier
        if config.get('AWS_REGION') == 'ap-south-1':
            print("\n⚠️  Note: ap-south-1 doesn't support free tier for EC2")
            print("   Switching to us-east-1 (US East) for free tier eligibility")
            config['AWS_REGION'] = 'us-east-1'
        
        return config
    except FileNotFoundError:
        print(f"✗ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in config file: {config_path}")
        sys.exit(1)

def validate_config(config):
    """Validate that all required credentials are present"""
    required_keys = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_REGION',
        'ANGEL_API_KEY',
        'ANGEL_CLIENT_CODE',
        'ANGEL_PASSWORD',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'TRADING_MODE'
    ]
    
    missing = [key for key in required_keys if key not in config or not config[key]]
    if missing:
        print(f"✗ Missing credentials: {', '.join(missing)}")
        sys.exit(1)
    print("✓ All required credentials present")
    return True

def get_latest_ubuntu_ami(ec2_client):
    """Get the latest Ubuntu 22.04 LTS AMI ID"""
    try:
        response = ec2_client.describe_images(
            Owners=['099720109477'],  # Canonical
            Filters=[
                {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'root-device-type', 'Values': ['ebs']},
                {'Name': 'virtualization-type', 'Values': ['hvm']}
            ]
        )
        
        if response['Images']:
            images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
            ami_id = images[0]['ImageId']
            print(f"✓ Using Ubuntu 22.04 LTS AMI: {ami_id}")
            return ami_id
        else:
            # Fallback AMIs for different regions
            fallback_amis = {
                'us-east-1': 'ami-0557a15b87f2b004d',
                'us-west-2': 'ami-0a8e758f5e873d1c1',
                'eu-west-1': 'ami-0d2a4a5d69e46ea0b'
            }
            ami_id = fallback_amis.get(ec2_client.meta.region_name, 'ami-0557a15b87f2b004d')
            print(f"✓ Using fallback Ubuntu AMI: {ami_id}")
            return ami_id
    except Exception as e:
        print(f"⚠️  Could not query AMIs: {str(e)}")
        fallback_amis = {
            'us-east-1': 'ami-0557a15b87f2b004d',
            'us-west-2': 'ami-0a8e758f5e873d1c1',
            'eu-west-1': 'ami-0d2a4a5d69e46ea0b'
        }
        ami_id = fallback_amis.get(ec2_client.meta.region_name, 'ami-0557a15b87f2b004d')
        print(f"✓ Using fallback Ubuntu AMI: {ami_id}")
        return ami_id

def create_ec2_instance(config):
    """Create EC2 instance with static IP"""
    print("\n=== Creating EC2 Instance ===")
    
    # Initialize AWS clients
    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    # Get latest Ubuntu AMI
    ami_id = get_latest_ubuntu_ami(ec2_client)
    
    # User data script to run on instance startup
    user_data_script = f"""#!/bin/bash
set -e

echo "Stock Yard Bot - EC2 Initialization Started"

# Update system
apt-get update
apt-get install -y python3-pip git curl

# Clone GitHub repository
cd /home/ubuntu
git clone https://github.com/anuragsin17-sketch/Stock-Yard.git
cd Stock-Yard

# Install Python dependencies
pip3 install -r requirements.txt 2>/dev/null || pip3 install yfinance pandas numpy requests python-telegram-bot

# Create configuration directory
mkdir -p /home/ubuntu/stock_yard_config

# Save credentials to config file (SECURE - permissions 600)
cat > /home/ubuntu/stock_yard_config/bot_config.json << 'EOF'
{{
    "ANGEL_API_KEY": "{config['ANGEL_API_KEY']}",
    "ANGEL_CLIENT_CODE": "{config['ANGEL_CLIENT_CODE']}",
    "ANGEL_PASSWORD": "{config['ANGEL_PASSWORD']}",
    "TELEGRAM_BOT_TOKEN": "{config['TELEGRAM_BOT_TOKEN']}",
    "TELEGRAM_CHAT_ID": "{config['TELEGRAM_CHAT_ID']}",
    "TRADING_MODE": "{config['TRADING_MODE']}"
}}
EOF
chmod 600 /home/ubuntu/stock_yard_config/bot_config.json

# Create systemd service for auto-restart
cat > /etc/systemd/system/stockyard-bot.service << 'SVCEOF'
[Unit]
Description=Stock Yard Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Stock-Yard
ExecStart=/usr/bin/python3 /home/ubuntu/Stock-Yard/run_trendline_scanner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

# Enable and start service
systemctl daemon-reload
systemctl enable stockyard-bot.service
systemctl start stockyard-bot.service

echo "Stock Yard Bot - EC2 Initialization Complete"
echo "Service running: stockyard-bot"
"""
    
    try:
        # Get or create security group
        vpc_id = ec2_client.describe_vpcs()['Vpcs'][0]['VpcId']
        
        # Use region-specific security group name to avoid conflicts
        sg_name = f'stockyard-bot-sg-{config["AWS_REGION"]}'
        
        # Try to get existing security group
        try:
            sg_response = ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': [sg_name]},
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ]
            )
            sg_id = sg_response['SecurityGroups'][0]['GroupId']
            print(f"✓ Using existing security group: {sg_id}")
        except:
            # Create new security group if it doesn't exist
            sg_response = ec2_client.create_security_group(
                GroupName=sg_name,
                Description='Security group for Stock Yard Trading Bot',
                VpcId=vpc_id
            )
            sg_id = sg_response['GroupId']
            print(f"✓ Created security group: {sg_id}")
        
        # Try to add security group rules (skip if already exist)
        try:
            ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print("✓ Configured security group rules")
        except Exception as e:
            if 'InvalidPermission.Duplicate' in str(e):
                print("✓ Security group rules already configured")
            else:
                raise
        
        # Launch EC2 instance (t3.micro - pay as you go, cheapest option)
        response = ec2_client.run_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType='t3.micro',
            SecurityGroupIds=[sg_id],
            UserData=user_data_script,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'StockYard-TradingBot'},
                        {'Key': 'Purpose', 'Value': 'Trendline Scanner'}
                    ]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"✓ Launched EC2 instance: {instance_id}")
        
        # Wait for instance to be running
        print("⏳ Waiting for instance to start (this takes 1-2 minutes)...")
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        print("✓ Instance is running")
        
        # Get instance details
        instances = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = instances['Reservations'][0]['Instances'][0]
        public_ip = instance.get('PublicIpAddress', 'N/A')
        private_ip = instance['PrivateIpAddress']
        
        print(f"  Instance ID: {instance_id}")
        print(f"  Public IP: {public_ip}")
        print(f"  Private IP: {private_ip}")
        print(f"  Region: {config['AWS_REGION']}")
        
        # Allocate Elastic IP (static IP)
        print("\n⏳ Allocating static IP...")
        eip_response = ec2_client.allocate_address(Domain='vpc')
        elastic_ip = eip_response['PublicIp']
        allocation_id = eip_response['AllocationId']
        
        # Associate Elastic IP with instance
        ec2_client.associate_address(
            InstanceId=instance_id,
            AllocationId=allocation_id
        )
        print(f"✓ Allocated static IP: {elastic_ip}")
        
        return {
            'instance_id': instance_id,
            'public_ip': elastic_ip,
            'private_ip': private_ip,
            'security_group': sg_id,
            'region': config['AWS_REGION']
        }
        
    except Exception as e:
        print(f"✗ Error creating EC2 instance: {str(e)}")
        sys.exit(1)

def print_summary(instance_info):
    """Print deployment summary and next steps"""
    print("\n" + "="*60)
    print("✓ AWS DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"\nInstance Details:")
    print(f"  Instance ID: {instance_info['instance_id']}")
    print(f"  Static IP: {instance_info['public_ip']}")
    print(f"  Private IP: {instance_info['private_ip']}")
    print(f"  Region: {instance_info.get('region', 'us-east-1')}")
    
    print(f"\n🎯 ANGEL ONE WHITELIST:")
    print(f"  Add this IP to Angel One API whitelist: {instance_info['public_ip']}")
    
    print(f"\n📱 TELEGRAM ALERTS:")
    print(f"  Bot will send alerts to your Telegram chat")
    print(f"  Status updates every 5 minutes")
    
    print(f"\n📊 MONITORING:")
    print(f"  SSH into instance: ssh -i your-key.pem ubuntu@{instance_info['public_ip']}")
    print(f"  View logs: journalctl -u stockyard-bot.service -f")
    print(f"  Check status: systemctl status stockyard-bot")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"  1. Whitelist {instance_info['public_ip']} in Angel One")
    print(f"  2. Wait 5 minutes for bot to initialize")
    print(f"  3. Check Telegram for first alert")
    print(f"  4. Monitor bot logs for any errors")
    
    print(f"\n⏰ Cost:")
    print(f"  t3.micro: ~₹200-300/month (pay as you go)")
    print(f"  Elastic IP: FREE when attached to running instance")
    print(f"  Total: ~₹200-300/month")
    print("="*60 + "\n")

def main():
    """Main deployment function"""
    print("\n" + "="*60)
    print("STOCK YARD TRADING BOT - AWS DEPLOYMENT")
    print("="*60)
    
    # Check if config file exists in Stock Yard folder
    config_path = Path('d:\\Stock Yard') / 'aws_config.json'
    if not config_path.exists():
        # Try Desktop as fallback
        config_path = Path.home() / 'Desktop' / 'aws_config.json'
        if not config_path.exists():
            print(f"✗ Config file not found")
            print(f"  Checked: d:\\Stock Yard\\aws_config.json")
            print(f"  Checked: {Path.home() / 'Desktop' / 'aws_config.json'}")
            print("Please save aws_config.json to Stock Yard folder")
            sys.exit(1)
    
    # Load and validate config
    config = load_config(config_path)
    validate_config(config)
    
    # Deploy to AWS
    print(f"\n🚀 Deploying to AWS Region: {config['AWS_REGION']}")
    print(f"📊 Trading Mode: {config['TRADING_MODE'].upper()}")
    
    instance_info = create_ec2_instance(config)
    
    # Print summary
    print_summary(instance_info)

if __name__ == '__main__':
    main()
