#!/usr/bin/env python3
"""
Deploy Telegram bot to EC2 via SCP and SSH
"""

import os
import subprocess
import json

# Read AWS config for credentials and IPs
with open('aws_config.json') as f:
    config = json.load(f)

EC2_IP = '32.194.58.75'
EC2_USER = 'ubuntu'
KEY_FILE = 'stock-yard-key.pem'  # EC2 private key in current folder

TELEGRAM_BOT_TOKEN = config['TELEGRAM_BOT_TOKEN']
TELEGRAM_CHAT_ID = config['TELEGRAM_CHAT_ID']

def run_command(cmd, description=""):
    """Run shell command"""
    if description:
        print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def deploy_bot():
    """Deploy bot files to EC2"""
    
    print("="*60)
    print("DEPLOYING TELEGRAM BOT TO EC2")
    print("="*60)
    
    # Files to copy
    files_to_copy = [
        'telegram_trade_bot.py',
        'telegram_webhook_server.py',
        'deploy_bot.sh'
    ]
    
    # Check if key file exists
    if not os.path.exists(KEY_FILE):
        print(f"❌ Key file not found: {KEY_FILE}")
        print(f"Please place your EC2 key pair file as: {KEY_FILE}")
        return False
    
    print(f"📋 Files to deploy:")
    for f in files_to_copy:
        print(f"   - {f}")
    
    print(f"\n📡 Target: {EC2_USER}@{EC2_IP}")
    
    # Test SSH connection
    print("\n🧪 Testing SSH connection...")
    success, output = run_command(
        f'ssh -i {KEY_FILE} -o StrictHostKeyChecking=no -o ConnectTimeout=5 {EC2_USER}@{EC2_IP} "echo OK"',
        ""
    )
    
    if not success:
        print(f"❌ Cannot connect to EC2: {output}")
        print("\nTroubleshooting:")
        print("1. Check if EC2 instance is running")
        print("2. Check if security group allows SSH (port 22)")
        print("3. Check if key file is correct")
        print("4. Check if key permissions: chmod 400 stock-yard-key.pem")
        return False
    
    print("✅ SSH connection successful")
    
    # Copy files
    print("\n📤 Copying files to EC2...")
    for file in files_to_copy:
        if not os.path.exists(file):
            print(f"⚠️  {file} not found, skipping...")
            continue
        
        success, output = run_command(
            f'scp -i {KEY_FILE} -o StrictHostKeyChecking=no {file} {EC2_USER}@{EC2_IP}:/home/ubuntu/{file}',
            f"Copying {file}..."
        )
        
        if success:
            print(f"✅ {file}")
        else:
            print(f"❌ {file}: {output}")
            return False
    
    # Make deploy script executable
    print("\n⚙️  Making deploy script executable...")
    success, output = run_command(
        f'ssh -i {KEY_FILE} -o StrictHostKeyChecking=no {EC2_USER}@{EC2_IP} "chmod +x /home/ubuntu/deploy_bot.sh"',
        ""
    )
    
    if success:
        print("✅ Permissions set")
    else:
        print(f"⚠️  Warning: {output}")
    
    # Run deployment script
    print("\n🚀 Running deployment script on EC2...")
    success, output = run_command(
        f'ssh -i {KEY_FILE} -o StrictHostKeyChecking=no {EC2_USER}@{EC2_IP} "bash /home/ubuntu/deploy_bot.sh"',
        ""
    )
    
    print(output)
    
    if not success:
        print(f"❌ Deployment failed")
        return False
    
    print("\n" + "="*60)
    print("✅ DEPLOYMENT COMPLETE!")
    print("="*60)
    
    print("\n🎉 Telegram Bot is now running on EC2!")
    print("\nWhat happens next:")
    print("1. Scanner finds a trendline signal")
    print("2. Sends Telegram alert with buttons")
    print("3. You click 'Confirm Trade'")
    print("4. Bot shows sizing options")
    print("5. You select quantity and confirm")
    print("6. Trade executes on Angel One API")
    
    return True


if __name__ == '__main__':
    print("📝 TELEGRAM BOT DEPLOYMENT TOOL")
    print()
    
    # Check for key file
    if not os.path.exists(KEY_FILE):
        print(f"❌ Error: SSH key file not found")
        print()
        print("To deploy to EC2, you need:")
        print(f"1. Place your EC2 private key as: {KEY_FILE}")
        print("2. Run: python deploy_to_ec2_ssh.py")
        print()
        print("Or manually SSH and run:")
        print(f"   ssh -i your-key.pem ubuntu@{EC2_IP}")
        print(f"   bash /home/ubuntu/deploy_bot.sh")
        exit(1)
    
    success = deploy_bot()
    exit(0 if success else 1)
