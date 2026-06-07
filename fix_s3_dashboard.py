#!/usr/bin/env python3
"""
Fix S3 Dashboard Deployment
Deletes old bucket and creates new one in correct region
"""

import json
import boto3
from pathlib import Path

def fix_s3_deployment(config_path='d:\\Stock Yard\\aws_config.json'):
    """Fix S3 dashboard deployment"""
    
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
    print("FIXING S3 DASHBOARD DEPLOYMENT")
    print("="*60 + "\n")
    
    # Step 1: Delete old bucket
    old_bucket = 'stockyard-dashboard-prod'
    print(f"⏳ Deleting old bucket: {old_bucket}...")
    try:
        # List all objects in bucket
        response = s3_client.list_objects_v2(Bucket=old_bucket)
        
        # Delete all objects
        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(Bucket=old_bucket, Key=obj['Key'])
            print(f"✓ Deleted {len(response['Contents'])} objects")
        
        # Delete bucket
        s3_client.delete_bucket(Bucket=old_bucket)
        print(f"✓ Old bucket deleted: {old_bucket}")
    except Exception as e:
        if 'NoSuchBucket' in str(e):
            print(f"✓ Old bucket doesn't exist (already deleted)")
        else:
            print(f"⚠️  Could not delete old bucket: {e}")
    
    # Step 2: Create new bucket in correct region with unique name
    print(f"\n⏳ Creating new bucket in {config['AWS_REGION']}...")
    import time
    bucket_name = f"stockyard-dashboard-{int(time.time())}"
    
    try:
        print(f"✓ Creating bucket: {bucket_name}")
        # For us-east-1, don't specify LocationConstraint
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✓ New bucket created: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
            print(f"✓ Bucket already exists (owned by you)")
        else:
            print(f"✗ Error creating bucket: {e}")
            return False
    
    # Step 3: Upload dashboard
    print(f"\n⏳ Uploading dashboard.html...")
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
        print("✓ Dashboard uploaded")
    except Exception as e:
        print(f"✗ Error uploading: {e}")
        return False
    
    # Step 4: Enable static website hosting
    print(f"\n⏳ Enabling static website hosting...")
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
        print(f"⚠️  Could not enable hosting: {e}")
    
    # Step 5: Set bucket policy for public access
    print(f"\n⏳ Setting bucket policy...")
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
        print("✓ Bucket policy set")
    except Exception as e:
        print(f"⚠️  Could not set policy: {e}")
    
    # Step 6: Block public access settings
    print(f"\n⏳ Configuring access settings...")
    try:
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print("✓ Access settings configured")
    except Exception as e:
        print(f"⚠️  Could not configure access: {e}")
    
    # Get dashboard URL
    dashboard_url = f"http://{bucket_name}.s3-website-{config['AWS_REGION']}.amazonaws.com"
    
    print("\n" + "="*60)
    print("✓ DASHBOARD FIXED AND DEPLOYED")
    print("="*60)
    print(f"\n🌐 Dashboard URL:\n   {dashboard_url}\n")
    print("📝 Note: It may take 2-3 minutes for the URL to become active")
    print("💡 If it still doesn't work:")
    print("   1. Wait 5 minutes")
    print("   2. Try a different browser")
    print("   3. Clear browser cache (Ctrl+Shift+Delete)\n")
    
    return True


if __name__ == '__main__':
    fix_s3_deployment()
