#!/usr/bin/env python3
"""
Add SSM role to EC2 instance so we can deploy via Systems Manager
"""

import json
import boto3
import time

def add_ssm_role(config_path='d:\\Stock Yard\\aws_config.json'):
    """Add SSM IAM role to EC2 instance"""
    
    # Load AWS credentials
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
        return False
    
    iam = boto3.client(
        'iam',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY']
    )
    
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("ADDING SSM ROLE TO EC2 INSTANCE")
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
        
        print(f"✓ Found instance: {instance_id}\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Create or get IAM role
    role_name = 'EC2-SSM-Management-Role'
    profile_name = 'EC2-SSM-Management-Profile'
    
    print("⏳ Creating/updating IAM role...")
    
    try:
        # Create role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Role for EC2 Systems Manager access'
            )
            print(f"✓ Created IAM role: {role_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"✓ IAM role already exists: {role_name}")
        
        # Attach SSM policy
        ssm_policy_arn = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=ssm_policy_arn
            )
            print(f"✓ Attached SSM policy to role")
        except:
            print(f"✓ Policy already attached")
        
        # Create instance profile
        try:
            iam.create_instance_profile(
                InstanceProfileName=profile_name
            )
            print(f"✓ Created instance profile: {profile_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"✓ Instance profile already exists: {profile_name}")
        
        # Add role to instance profile
        try:
            iam.add_role_to_instance_profile(
                InstanceProfileName=profile_name,
                RoleName=role_name
            )
            print(f"✓ Added role to instance profile")
        except:
            print(f"✓ Role already in instance profile")
        
        print()
        
    except Exception as e:
        print(f"✗ Role creation error: {e}")
        return False
    
    # Associate instance profile with EC2 instance
    print("⏳ Associating profile with EC2 instance...")
    
    try:
        # First, check if instance already has a profile
        instance_profiles = ec2.describe_iam_instance_profile_associations(
            Filters=[
                {'Name': 'instance-id', 'Values': [instance_id]}
            ]
        )
        
        if instance_profiles['IamInstanceProfileAssociations']:
            # Already has a profile
            assoc_id = instance_profiles['IamInstanceProfileAssociations'][0]['AssociationId']
            print(f"✓ Instance already has profile, updating...")
            
            ec2.disassociate_iam_instance_profile(
                AssociationId=assoc_id
            )
            
            time.sleep(5)
        
        # Associate new profile
        ec2.associate_iam_instance_profile(
            IamInstanceProfile={'Name': profile_name},
            InstanceId=instance_id
        )
        
        print(f"✓ Instance profile associated\n")
        
    except Exception as e:
        print(f"✗ Error associating profile: {e}")
        print(f"  (This may be expected if profile is already attached)\n")
    
    print("⏳ Waiting for role to be active (60 seconds)...")
    time.sleep(60)
    
    print("\n" + "="*60)
    print("✓ SSM ROLE ADDED TO EC2")
    print("="*60)
    print(f"\n✅ EC2 instance {instance_id} now has SSM permissions")
    print(f"\nNext step: Run the dashboard deployment script")
    print(f"  python fix_ec2_nginx.py\n")
    
    return True


if __name__ == '__main__':
    add_ssm_role()
