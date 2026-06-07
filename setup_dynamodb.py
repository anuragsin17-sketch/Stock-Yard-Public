#!/usr/bin/env python3
"""
Setup DynamoDB Database for Trade History
Stores alerts, trades, and performance metrics
"""

import json
import boto3
from datetime import datetime

def setup_dynamodb(config_path='d:\\Stock Yard\\aws_config.json'):
    """Create DynamoDB tables for trade tracking"""
    
    # Load AWS credentials
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        print("✗ Could not load AWS config")
        return False
    
    # Initialize DynamoDB
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n" + "="*60)
    print("SETTING UP DYNAMODB DATABASE")
    print("="*60 + "\n")
    
    # Table 1: Stock Alerts
    print("⏳ Creating 'StockAlerts' table...")
    try:
        alerts_table = dynamodb.create_table(
            TableName='StockAlerts',
            KeySchema=[
                {'AttributeName': 'timestamp', 'KeyType': 'HASH'},
                {'AttributeName': 'ticker', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'ticker', 'AttributeType': 'S'},
                {'AttributeName': 'tab_type', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'TabTypeIndex',
                    'KeySchema': [
                        {'AttributeName': 'tab_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        alerts_table.wait_until_exists()
        print("✓ StockAlerts table created")
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print("✓ StockAlerts table already exists")
        else:
            print(f"✗ Error creating table: {e}")
    
    # Table 2: Trade History
    print("⏳ Creating 'TradeHistory' table...")
    try:
        trades_table = dynamodb.create_table(
            TableName='TradeHistory',
            KeySchema=[
                {'AttributeName': 'trade_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'trade_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'ticker', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'TickerIndex',
                    'KeySchema': [
                        {'AttributeName': 'ticker', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        trades_table.wait_until_exists()
        print("✓ TradeHistory table created")
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print("✓ TradeHistory table already exists")
        else:
            print(f"✗ Error creating table: {e}")
    
    # Table 3: Performance Metrics
    print("⏳ Creating 'PerformanceMetrics' table...")
    try:
        metrics_table = dynamodb.create_table(
            TableName='PerformanceMetrics',
            KeySchema=[
                {'AttributeName': 'metric_date', 'KeyType': 'HASH'},
                {'AttributeName': 'metric_type', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'metric_date', 'AttributeType': 'S'},
                {'AttributeName': 'metric_type', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        metrics_table.wait_until_exists()
        print("✓ PerformanceMetrics table created")
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print("✓ PerformanceMetrics table already exists")
        else:
            print(f"✗ Error creating table: {e}")
    
    print("\n" + "="*60)
    print("✓ DYNAMODB SETUP COMPLETE")
    print("="*60)
    print("\nDatabase Schema:")
    print("\n📊 StockAlerts Table:")
    print("   - timestamp (Date/Time of alert)")
    print("   - ticker (Stock symbol)")
    print("   - tab_type (volume, trendline, radar)")
    print("   - price (Stock price)")
    print("   - status (new, critical, watchlist)")
    print("\n💹 TradeHistory Table:")
    print("   - trade_id (Unique trade ID)")
    print("   - timestamp (Trade execution time)")
    print("   - ticker (Stock symbol)")
    print("   - entry_price (Entry price)")
    print("   - exit_price (Exit price)")
    print("   - quantity (Shares bought)")
    print("   - pnl (Profit/Loss)")
    print("   - status (open, closed, cancelled)")
    print("\n📈 PerformanceMetrics Table:")
    print("   - metric_date (Daily/Monthly/Yearly)")
    print("   - win_rate (% wins)")
    print("   - total_trades (Count)")
    print("   - total_pnl (Total profit/loss)")
    print("   - best_trade (Best trade value)")
    print("   - worst_trade (Worst trade value)")
    print("\n✅ All tables use FREE tier with on-demand billing")
    print("💰 Cost: ~$1-2/month after free tier\n")
    
    return True


def insert_sample_data(config_path='d:\\Stock Yard\\aws_config.json'):
    """Insert sample trade data for testing"""
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        return False
    
    from decimal import Decimal
    
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
        region_name=config['AWS_REGION']
    )
    
    print("\n⏳ Inserting sample trade data...")
    
    try:
        # Sample alerts
        alerts_table = dynamodb.Table('StockAlerts')
        alerts_table.put_item(Item={
            'timestamp': datetime.now().isoformat(),
            'ticker': 'RELIANCE',
            'tab_type': 'volume',
            'price': Decimal('2500'),
            'status': 'new',
            'volume': '50M'
        })
        
        # Sample trades
        trades_table = dynamodb.Table('TradeHistory')
        trades_table.put_item(Item={
            'trade_id': 'TRADE_001',
            'timestamp': datetime.now().isoformat(),
            'ticker': 'TCS',
            'entry_price': Decimal('3500'),
            'exit_price': Decimal('3650'),
            'quantity': Decimal('14'),
            'pnl': Decimal('2100'),
            'status': 'closed'
        })
        
        # Sample metrics
        metrics_table = dynamodb.Table('PerformanceMetrics')
        metrics_table.put_item(Item={
            'metric_date': datetime.now().strftime('%Y-%m-%d'),
            'metric_type': 'daily',
            'win_rate': Decimal('61.88'),
            'total_trades': Decimal('5'),
            'total_pnl': Decimal('12500'),
            'best_trade': Decimal('3500'),
            'worst_trade': Decimal('-1200')
        })
        
        print("✓ Sample data inserted\n")
        return True
    except Exception as e:
        print(f"✗ Error inserting sample data: {e}\n")
        return False


if __name__ == '__main__':
    setup_dynamodb()
    insert_sample_data()
