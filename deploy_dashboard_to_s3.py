#!/usr/bin/env python3
"""
Deploy Dashboard to AWS S3
Uploads HTML dashboard and configures for web hosting
"""

import json
import boto3
from pathlib import Path

def deploy_dashboard_to_s3(config_path='d:\\Stock Yard\\aws_config.json'):
    """Deploy dashboard to S3"""
    
    # Load AWS credentials
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
        return False
    
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("DEPLOYING DASHBOARD TO AWS S3")
    print("="*60 + "\n")
    
    # Create S3 bucket with unique name
    bucket_name = f'stockyard-dashboard-{config["AWS_ACCESS_KEY_ID"][-8:].lower()}'
    
    try:
        print(f"⏳ Creating S3 bucket: {bucket_name}...")
        if config['AWS_REGION'] == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': config['AWS_REGION']}
            )
        print(f"✓ S3 bucket created: {bucket_name}")
    except s3_client.exceptions.BucketAlreadyExists:
        print(f"✓ S3 bucket already exists: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e) or 'BucketAlreadyExists' in str(e):
            print(f"✓ S3 bucket exists: {bucket_name}")
        else:
            print(f"✗ Error creating bucket: {e}")
            return False
    
    # Upload dashboard HTML
    print("\n⏳ Uploading dashboard.html...")
    try:
        dashboard_path = Path('d:\\Stock Yard\\dashboard.html')
        with open(dashboard_path, 'rb') as f:
            s3_client.upload_fileobj(
                f,
                bucket_name,
                'index.html',
                ExtraArgs={
                    'ContentType': 'text/html',
                    'CacheControl': 'max-age=3600'
                }
            )
        print("✓ Dashboard uploaded as index.html")
    except Exception as e:
        print(f"✗ Error uploading dashboard: {e}")
        return False
    
    # Enable static website hosting
    print("\n⏳ Configuring S3 for static website hosting...")
    try:
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'index.html'}
            }
        )
        print("✓ Static website hosting enabled")
    except Exception as e:
        print(f"✗ Error configuring website: {e}")
    
    # Make bucket public (read-only)
    print("\n⏳ Configuring bucket permissions...")
    try:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy)
        )
        print("✓ Bucket policy set (public read)")
    except Exception as e:
        print(f"⚠️  Could not set bucket policy: {e}")
    
    # Get dashboard URL
    dashboard_url = f"http://{bucket_name}.s3-website-{config['AWS_REGION']}.amazonaws.com"
    
    print("\n" + "="*60)
    print("✓ DASHBOARD DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"\n🌐 Dashboard URL:\n   {dashboard_url}\n")
    print("📱 Works on:")
    print("   • Chrome (Desktop & Mobile)")
    print("   • Safari (Desktop & Mobile)")
    print("   • Firefox, Edge, and all modern browsers\n")
    print("📲 To share via Telegram:")
    print("   • Open dashboard → Click '📱 Share Link' button")
    print("   • Telegram opens → Send to friends\n")
    print("⏱️  Auto-refreshes every 5 minutes")
    print("🔄 Click 'Refresh' button to update manually\n")
    
    return dashboard_url


if __name__ == '__main__':
    deploy_dashboard_to_s3()
