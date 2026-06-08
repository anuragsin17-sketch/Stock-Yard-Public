#!/usr/bin/env python3
"""
Verification Script for Telegram Webhook Deployment
Tests connectivity, service status, webhook registration, and end-to-end functionality
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Configuration
EC2_IP = "32.194.58.75"
EC2_USER = "ubuntu"
WEBHOOK_URL = f"https://{EC2_IP}/webhook/telegram"
HEALTH_URL = f"https://{EC2_IP}/health"


class Verify:
    """Verification utilities"""
    
    def __init__(self, ssh_key: Optional[str] = None):
        self.ssh_key = ssh_key or self._find_ssh_key()
        self.results = []
    
    @staticmethod
    def _find_ssh_key() -> Optional[str]:
        """Find SSH key"""
        possible = [
            "stock-yard-key.pem",
            Path.home() / ".ssh" / "stock-yard-key.pem",
        ]
        for p in possible:
            if Path(p).exists():
                return str(p)
        return None
    
    @staticmethod
    def _log(color: str, symbol: str, msg: str):
        """Log with color"""
        print(f"{color}{symbol}{RESET} {msg}")
    
    def info(self, msg: str):
        self._log(GREEN, "✓", msg)
    
    def error(self, msg: str):
        self._log(RED, "✗", msg)
    
    def warn(self, msg: str):
        self._log(YELLOW, "⚠", msg)
    
    def step(self, msg: str):
        self._log(BLUE, "→", msg)
    
    def test(self, name: str, result: bool, details: str = ""):
        """Record test result"""
        status = "PASS" if result else "FAIL"
        color = GREEN if result else RED
        symbol = "✓" if result else "✗"
        
        self._log(color, symbol, f"{name}: {status}")
        if details:
            print(f"  {details}")
        
        self.results.append({
            'test': name,
            'status': status,
            'details': details
        })
    
    def print_summary(self):
        """Print test summary"""
        print()
        print(f"{BLUE}{'=' * 50}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{BLUE}{'=' * 50}{RESET}")
        print()
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        
        for result in self.results:
            color = GREEN if result['status'] == 'PASS' else RED
            print(f"{color}{result['status']}{RESET} - {result['test']}")
            if result['details']:
                print(f"     {result['details']}")
        
        print()
        print(f"Total: {len(self.results)} | {GREEN}Passed: {passed}{RESET} | {RED}Failed: {failed}{RESET}")
        print()
        
        return failed == 0


def verify_ssh_connectivity(verifier: Verify) -> bool:
    """Verify SSH connectivity to EC2"""
    verifier.step("Testing SSH connectivity...")
    
    if not verifier.ssh_key:
        verifier.error("SSH key not found")
        return False
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{EC2_USER}@{EC2_IP}",
        "echo 'SSH connection OK'"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            verifier.test("SSH Connectivity", True, f"Connected to {EC2_IP}")
            return True
        else:
            verifier.test("SSH Connectivity", False, f"SSH returned: {result.stderr[:100]}")
            return False
    except Exception as e:
        verifier.test("SSH Connectivity", False, str(e))
        return False


def verify_service_status(verifier: Verify) -> bool:
    """Verify systemd service is running"""
    verifier.step("Checking service status...")
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        "-o", "ConnectTimeout=5",
        f"{EC2_USER}@{EC2_IP}",
        "sudo systemctl is-active telegram-webhook"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "active" in result.stdout:
            verifier.test("Service Status", True, "telegram-webhook is active")
            return True
        else:
            verifier.test("Service Status", False, "Service not running")
            
            # Get more details
            cmd_logs = [
                "ssh",
                "-i", verifier.ssh_key,
                f"{EC2_USER}@{EC2_IP}",
                "sudo journalctl -u telegram-webhook -n 5 --no-pager"
            ]
            
            log_result = subprocess.run(cmd_logs, capture_output=True, text=True)
            if log_result.stdout:
                print(f"  Recent logs: {log_result.stdout[:200]}")
            
            return False
    except Exception as e:
        verifier.test("Service Status", False, str(e))
        return False


def verify_port_listening(verifier: Verify) -> bool:
    """Verify port 443 is listening"""
    verifier.step("Checking if port 443 is listening...")
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        f"{EC2_USER}@{EC2_IP}",
        "sudo netstat -tlnp 2>/dev/null | grep 443 || sudo ss -tlnp 2>/dev/null | grep 443"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "443" in result.stdout:
            verifier.test("Port 443 Listening", True, "Port is open")
            return True
        else:
            verifier.test("Port 443 Listening", False, "Port not listening")
            return False
    except Exception as e:
        verifier.test("Port 443 Listening", False, str(e))
        return False


def verify_ssl_certificate(verifier: Verify) -> bool:
    """Verify SSL certificate exists"""
    verifier.step("Checking SSL certificate...")
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        f"{EC2_USER}@{EC2_IP}",
        "ls -la /home/ubuntu/telegram_webhook/certs/"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if ".crt" in result.stdout and ".key" in result.stdout:
            verifier.test("SSL Certificate", True, "Certificate files exist")
            return True
        else:
            verifier.test("SSL Certificate", False, "Certificate files not found")
            return False
    except Exception as e:
        verifier.test("SSL Certificate", False, str(e))
        return False


def verify_health_endpoint(verifier: Verify) -> bool:
    """Verify health check endpoint"""
    verifier.step("Testing health endpoint...")
    
    try:
        response = requests.get(HEALTH_URL, verify=False, timeout=5)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'status' in data and data['status'] == 'healthy':
                    verifier.test("Health Endpoint", True, "Webhook is responding")
                    return True
            except:
                verifier.test("Health Endpoint", True, "Endpoint responding (status code 200)")
                return True
        else:
            verifier.test("Health Endpoint", False, f"Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        verifier.test("Health Endpoint", False, f"Request failed: {str(e)[:50]}")
        return False


def verify_telegram_webhook_registration(verifier: Verify, token: str) -> bool:
    """Verify Telegram webhook is registered"""
    verifier.step("Checking Telegram webhook registration...")
    
    try:
        # Get webhook info from Telegram
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.post(url, verify=False, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ok'):
                webhook_info = data.get('result', {})
                registered_url = webhook_info.get('url', '')
                
                if WEBHOOK_URL in registered_url:
                    verifier.test("Telegram Webhook", True, f"Registered: {registered_url}")
                    return True
                else:
                    verifier.test("Telegram Webhook", False, f"Different URL registered: {registered_url}")
                    return False
            else:
                error = data.get('description', 'Unknown error')
                verifier.test("Telegram Webhook", False, f"Telegram error: {error}")
                return False
        else:
            verifier.test("Telegram Webhook", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        verifier.test("Telegram Webhook", False, str(e))
        return False


def test_webhook_with_sample_callback(verifier: Verify) -> bool:
    """Test webhook with a sample callback query"""
    verifier.step("Testing webhook with sample callback...")
    
    try:
        # Create a sample callback query (this won't actually execute a trade)
        sample_callback = {
            'update_id': 123456789,
            'callback_query': {
                'id': 'test_callback_123',
                'from': {'id': 123, 'first_name': 'Test'},
                'chat_instance': '123',
                'data': 'confirm_trade:INFY:1500.50:1800.00:1380.00:10',
                'message': {'message_id': 1, 'chat': {'id': 123}}
            }
        }
        
        response = requests.post(WEBHOOK_URL, json=sample_callback, verify=False, timeout=5)
        
        if response.status_code == 200:
            verifier.test("Sample Webhook Call", True, "Webhook accepted callback")
            return True
        else:
            verifier.test("Sample Webhook Call", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        verifier.test("Sample Webhook Call", False, str(e))
        return False


def verify_telegram_env_variables(verifier: Verify) -> bool:
    """Verify environment variables are set on EC2"""
    verifier.step("Checking environment variables on EC2...")
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        f"{EC2_USER}@{EC2_IP}",
        "sudo systemctl show-environment | grep -E 'TELEGRAM_|ANGEL_' || echo 'No service env'"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if "TELEGRAM_BOT_TOKEN" in result.stdout:
            verifier.test("Environment Variables", True, "Variables set in systemd")
            return True
        else:
            verifier.test("Environment Variables", False, "Variables not found in service")
            return False
    except Exception as e:
        verifier.test("Environment Variables", False, str(e))
        return False


def verify_application_files(verifier: Verify) -> bool:
    """Verify application files are deployed"""
    verifier.step("Checking application files...")
    
    cmd = [
        "ssh",
        "-i", verifier.ssh_key,
        f"{EC2_USER}@{EC2_IP}",
        "ls -la /home/ubuntu/telegram_webhook/ | grep -E '\\.py|webhook'"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if "webhook.py" in result.stdout or "run_webhook.py" in result.stdout:
            verifier.test("Application Files", True, "Files deployed")
            return True
        else:
            verifier.test("Application Files", False, "Files not found")
            return False
    except Exception as e:
        verifier.test("Application Files", False, str(e))
        return False


def main():
    """Main verification flow"""
    
    print()
    print(f"{BLUE}{'=' * 50}{RESET}")
    print(f"{BLUE}TELEGRAM WEBHOOK DEPLOYMENT VERIFICATION{RESET}")
    print(f"{BLUE}{'=' * 50}{RESET}")
    print()
    
    # Initialize verifier
    verifier = Verify()
    
    if not verifier.ssh_key:
        print(f"{RED}✗ SSH key not found{RESET}")
        print("Please place stock-yard-key.pem in current directory or ~/.ssh/")
        sys.exit(1)
    
    print(f"SSH Key: {verifier.ssh_key}")
    print(f"EC2 Host: {EC2_IP}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()
    
    # Read environment variables for Telegram token
    env_vars = {}
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        k, v = line.strip().split('=', 1)
                        env_vars[k.strip()] = v.strip()
        except:
            pass
    
    telegram_token = env_vars.get('TELEGRAM_BOT_TOKEN', '')
    
    # Run verification tests
    print(f"{BLUE}Running Verification Tests...{RESET}")
    print()
    
    verify_ssh_connectivity(verifier)
    verify_service_status(verifier)
    verify_port_listening(verifier)
    verify_ssl_certificate(verifier)
    verify_application_files(verifier)
    verify_telegram_env_variables(verifier)
    
    print()
    
    verify_health_endpoint(verifier)
    
    if telegram_token:
        verify_telegram_webhook_registration(verifier, telegram_token)
        test_webhook_with_sample_callback(verifier)
    else:
        verifier.warn("Telegram token not found in .env - skipping Telegram tests")
    
    # Print summary
    all_passed = verifier.print_summary()
    
    if all_passed:
        print(f"{GREEN}✓ All verification tests passed!{RESET}")
        print()
        print("Deployment is complete and working correctly.")
        print()
        print("Next: Test with actual Telegram alert:")
        print("  1. Trigger an alert from your screener")
        print("  2. Click 'Confirm Trade' button in Telegram")
        print("  3. Check if trade executes")
        print()
        print("Monitor logs with:")
        print(f"  ssh -i {verifier.ssh_key} ubuntu@{EC2_IP} 'sudo journalctl -u telegram-webhook -f'")
    else:
        print(f"{RED}✗ Some tests failed. Check output above.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    # Suppress SSL warnings for self-signed certificate
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nVerification cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}✗ Error: {e}{RESET}")
        sys.exit(1)
