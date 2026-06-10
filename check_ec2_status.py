#!/usr/bin/env python3
"""Check if EC2 API service is running"""

import requests
import sys

EC2_URL = "http://32.194.58.75:5000"

print("\n" + "="*70)
print("🔍 CHECKING EC2 API SERVICE STATUS")
print("="*70)

print(f"\nTarget: {EC2_URL}")
print("\nTesting endpoints...")

# Test 1: Health check
print("\n1️⃣  Health endpoint (/health)...")
try:
    response = requests.get(f"{EC2_URL}/health", timeout=5)
    if response.status_code == 200:
        print(f"   ✅ Service is RUNNING")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Service: {data.get('service')}")
    else:
        print(f"   ❌ Service responded but with error: HTTP {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ CANNOT CONNECT - EC2 service is NOT RUNNING")
except requests.exceptions.Timeout:
    print(f"   ⏱️  TIMEOUT - EC2 is slow or not responding")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Sync trades endpoint
print("\n2️⃣  Sync endpoint (/api/sync-trades)...")
try:
    response = requests.get(f"{EC2_URL}/api/sync-trades", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Endpoint is WORKING")
        print(f"   Open trades synced: {data.get('radar_trades')}")
        print(f"   Closed trades: {data.get('closed_trades')}")
    else:
        print(f"   ❌ HTTP {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)

try:
    response = requests.get(f"{EC2_URL}/health", timeout=5)
    if response.status_code == 200:
        print("\n✅ EC2 SERVICE IS RUNNING")
        print("\nNext steps:")
        print("1. Run: python manual_sync_radar.py")
        print("2. Open dashboard Radar tab")
        print("3. Your 2 Angel One trades should appear")
    else:
        print(f"\n⚠️  EC2 service is having issues (HTTP {response.status_code})")
except:
    print("\n❌ EC2 SERVICE IS NOT RUNNING")
    print("\nTo fix this:")
    print("1. Check the 'Deploy Angel Order Handler to EC2' workflow")
    print("2. If it failed, check the logs for errors")
    print("3. If it succeeded, SSH to EC2 and check:")
    print("   ssh ubuntu@32.194.58.75")
    print("   sudo systemctl status angel-api")
    print("   sudo journalctl -u angel-api -n 50")

print()
