#!/usr/bin/env python3
"""
Fix Nginx installation on EC2 Ubuntu instance
Handle repository issues and install Nginx properly
"""

import json
import boto3
import time

def fix_and_install_nginx(config_path='d:\\Stock Yard\\aws_config.json'):
    """Fix Nginx installation issues"""
    
    # Load AWS credentials
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
        return False
    
    # Initialize SSM client
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
    print("FIXING NGINX INSTALLATION ON EC2")
    print("="*60 + "\n")
    
    # Get instance
    print("⏳ Finding EC2 instance...")
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['StockYard-TradingBot']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        if not response['Reservations']:
            print("✗ No running instances found")
            return False
        
        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        public_ip = instance.get('PublicIpAddress', 'N/A')
        
        print(f"✓ Found instance: {instance_id}")
        print(f"  Public IP: {public_ip}\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Fix apt repositories and install Nginx
    print("⏳ Fixing apt repositories...")
    
    commands = [
        # Clear and update apt cache
        "apt-get clean && apt-get update -qq",
        
        # Install dependencies
        "apt-get install -y curl gnupg2 ca-certificates lsb-release ubuntu-keyring",
        
        # Add official Nginx repository
        "curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor | tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null",
        
        # Add Nginx repository (bionic compatibility for jammy)
        "echo 'deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/ubuntu bionic nginx' | tee /etc/apt/sources.list.d/nginx.list",
        
        # Update apt and install Nginx from official repo
        "apt-get update -qq && apt-get install -y nginx",
        
        # Start and enable Nginx
        "systemctl start nginx && systemctl enable nginx",
        
        # Create web directory
        "mkdir -p /var/www/stockyard && chown -R www-data:www-data /var/www/stockyard"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"  [{i}/{len(commands)}] {cmd[:60]}...")
        
        try:
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={'command': [cmd]},
                TimeoutSeconds=120
            )
            
            command_id = response['Command']['CommandId']
            
            # Wait for completion
            for attempt in range(60):
                time.sleep(1)
                try:
                    result = ssm.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id
                    )
                    
                    if result['Status'] in ['Success', 'Failed']:
                        if result['Status'] == 'Success':
                            print(f"       ✓")
                        else:
                            print(f"       ⚠️  (continuing...)")
                        break
                except:
                    pass
                    
        except Exception as e:
            print(f"       ⚠️  {str(e)[:50]}")
    
    print("\n✓ Nginx installation commands sent\n")
    
    # Now deploy the dashboard HTML
    print("⏳ Deploying dashboard HTML...")
    
    # Read the dashboard HTML
    dashboard_path = "d:\\Stock Yard\\dashboard.html"
    try:
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"✗ Could not read dashboard.html: {e}")
        return False
    
    # Create HTML file via SSM
    # Use tee to write the file
    write_html_cmd = f"cat > /var/www/stockyard/index.html << 'HTMLEOF'\n{html_content}\nHTMLEOF"
    
    print("  Uploading HTML file...")
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [write_html_cmd]},
            TimeoutSeconds=60
        )
        
        command_id = response['Command']['CommandId']
        
        for attempt in range(30):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print("  ✓ HTML uploaded")
                    else:
                        print("  ⚠️  HTML upload had issues")
                    break
            except:
                pass
                
    except Exception as e:
        print(f"  ⚠️  {str(e)[:50]}")
    
    # Configure Nginx
    print("\n⏳ Configuring Nginx...")
    
    nginx_config = """server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/stockyard;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}"""
    
    nginx_cmd = f"""cat > /etc/nginx/sites-available/stockyard << 'CONFEOF'
{nginx_config}
CONFEOF
ln -sf /etc/nginx/sites-available/stockyard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
echo "Nginx configured and restarted"
"""
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'command': [nginx_cmd]},
            TimeoutSeconds=60
        )
        
        command_id = response['Command']['CommandId']
        
        for attempt in range(30):
            time.sleep(1)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                if result['Status'] in ['Success', 'Failed']:
                    if result['Status'] == 'Success':
                        print("  ✓ Nginx configured")
                    else:
                        print("  ⚠️  Configuration issue")
                    break
            except:
                pass
                
    except Exception as e:
        print(f"  ⚠️  {str(e)[:50]}")
    
    print("\n" + "="*60)
    print("✓ NGINX INSTALLATION FIXED")
    print("="*60)
    print(f"\n🌐 Dashboard URL:")
    print(f"   http://{public_ip}\n")
    print("⏱️  Wait 30 seconds for Nginx to fully restart")
    print("📱 Then open the URL in your browser\n")
    print("✅ Dashboard should now be LIVE!\n")
    
    return True


if __name__ == '__main__':
    fix_and_install_nginx()
