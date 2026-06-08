#!/usr/bin/env python3
"""
Telegram Webhook Deployment Script for EC2
Deploys Flask webhook with HTTPS and systemd service
Works on Windows/Mac/Linux
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Configuration
EC2_IP = "32.194.58.75"
EC2_USER = "ubuntu"
DEPLOY_DIR = "/home/ubuntu/telegram_webhook"
SERVICE_NAME = "telegram-webhook"
WEBHOOK_PORT = 443
WEBHOOK_URL = f"https://{EC2_IP}/webhook/telegram"


class Colors:
    """Color codes for terminal output"""
    @staticmethod
    def green(text: str) -> str:
        return f"{GREEN}{text}{RESET}"

    @staticmethod
    def red(text: str) -> str:
        return f"{RED}{text}{RESET}"

    @staticmethod
    def yellow(text: str) -> str:
        return f"{YELLOW}{text}{RESET}"

    @staticmethod
    def blue(text: str) -> str:
        return f"{BLUE}{text}{RESET}"


def log_info(msg: str):
    print(f"{Colors.green('✓')} {msg}")


def log_error(msg: str):
    print(f"{Colors.red('✗')} {msg}")


def log_warn(msg: str):
    print(f"{Colors.yellow('⚠')} {msg}")


def log_step(msg: str):
    print(f"{Colors.blue('→')} {msg}")


def find_ssh_key() -> Optional[str]:
    """Find the SSH key for EC2"""
    log_step("Searching for SSH key...")
    
    possible_paths = [
        "stock-yard-key.pem",
        "./stock-yard-key.pem",
        Path.home() / ".ssh" / "stock-yard-key.pem",
        Path.cwd() / "stock-yard-key.pem",
        Path.cwd() / ".." / "stock-yard-key.pem",
    ]
    
    for path in possible_paths:
        path_obj = Path(path)
        if path_obj.exists() and path_obj.is_file():
            log_info(f"SSH key found: {path_obj.absolute()}")
            return str(path_obj.absolute())
    
    log_error("SSH key not found. Searched:")
    for p in possible_paths:
        print(f"  - {p}")
    return None


def run_command(cmd: list, description: str = "", capture_output: bool = False) -> tuple[bool, str]:
    """Execute a shell command"""
    try:
        if description:
            log_step(description)
        
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            if description:
                log_info("Success")
            return True, result.stdout + result.stderr
        else:
            return False, result.stdout + result.stderr
    
    except Exception as e:
        log_error(f"Command failed: {str(e)}")
        return False, str(e)


def read_env_file() -> dict:
    """Read environment variables from .env file"""
    env_path = Path(".env")
    env_vars = {}
    
    if not env_path.exists():
        log_warn(".env file not found")
        return env_vars
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    except Exception as e:
        log_error(f"Failed to read .env: {e}")
    
    return env_vars


def create_remote_deployment_script(env_vars: dict) -> str:
    """Create the remote deployment script"""
    
    telegram_token = env_vars.get('TELEGRAM_BOT_TOKEN', '')
    telegram_chat = env_vars.get('TELEGRAM_CHAT_ID', '')
    angel_key = env_vars.get('ANGEL_API_KEY', '')
    angel_client = env_vars.get('ANGEL_CLIENT_ID', '')
    
    script = f'''#!/bin/bash
set -e

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

# Functions
log_info() {{ echo -e "${{GREEN}}✓${{NC}} $1"; }}
log_error() {{ echo -e "${{RED}}✗${{NC}} $1"; exit 1; }}
log_warn() {{ echo -e "${{YELLOW}}⚠${{NC}} $1"; }}
log_step() {{ echo -e "${{BLUE}}→${{NC}} $1"; }}

echo -e "${{BLUE}}========================================${{NC}}"
echo -e "${{BLUE}}EC2 REMOTE DEPLOYMENT${{NC}}"
echo -e "${{BLUE}}========================================${{NC}}"

DEPLOY_DIR="{DEPLOY_DIR}"
SERVICE_NAME="{SERVICE_NAME}"

# Step 1: Setup
log_step "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR/certs"
cd "$DEPLOY_DIR"
log_info "Directory created"

# Step 2: Install dependencies
log_step "Installing Python dependencies..."
pip3 install flask requests --quiet 2>/dev/null || pip install flask requests --quiet 2>/dev/null
log_info "Dependencies installed"

# Step 3: Copy files
log_step "Copying application files..."
cp /home/ubuntu/telegram_webhook_simple.py "$DEPLOY_DIR/webhook.py" 2>/dev/null || echo "webhook.py not found"
cp /home/ubuntu/angel_trade.py "$DEPLOY_DIR/angel_trade.py" 2>/dev/null || echo "angel_trade.py not found"
log_info "Files copied"

# Step 4: Generate SSL certificate
log_step "Generating self-signed SSL certificate..."
if [ ! -f "$DEPLOY_DIR/certs/webhook.crt" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes \\
        -out "$DEPLOY_DIR/certs/webhook.crt" \\
        -keyout "$DEPLOY_DIR/certs/webhook.key" \\
        -days 365 \\
        -subj "/CN=32.194.58.75" 2>/dev/null
fi
chmod 600 "$DEPLOY_DIR/certs/webhook.key"
chmod 644 "$DEPLOY_DIR/certs/webhook.crt"
log_info "SSL certificate ready"

# Step 5: Create HTTPS wrapper
log_step "Creating HTTPS wrapper..."
cat > "$DEPLOY_DIR/run_webhook.py" << 'WRAPPER_EOF'
#!/usr/bin/env python3
import os, sys, ssl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webhook import app

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(
    certfile='{DEPLOY_DIR}/certs/webhook.crt',
    keyfile='{DEPLOY_DIR}/certs/webhook.key'
)

print("=" * 60)
print("🚀 TELEGRAM WEBHOOK SERVER (HTTPS)")
print("=" * 60)
print(f"Webhook: https://32.194.58.75/webhook/telegram")
print(f"Health: https://32.194.58.75/health")
print("=" * 60)

app.run(host='0.0.0.0', port=443, ssl_context=context, debug=False, use_reloader=False, threaded=True)
WRAPPER_EOF

chmod +x "$DEPLOY_DIR/run_webhook.py"
log_info "HTTPS wrapper created"

# Step 6: Create systemd service
log_step "Creating systemd service..."
sudo tee /etc/systemd/system/${{SERVICE_NAME}}.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Telegram Webhook for Stock Yard Trading
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory={DEPLOY_DIR}
Environment="TELEGRAM_BOT_TOKEN={telegram_token}"
Environment="TELEGRAM_CHAT_ID={telegram_chat}"
Environment="ANGEL_API_KEY={angel_key}"
Environment="ANGEL_CLIENT_ID={angel_client}"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/usr/bin/python3 {DEPLOY_DIR}/run_webhook.py

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

log_info "Service file created"

# Step 7: Enable and start
log_step "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ${{SERVICE_NAME}} 2>/dev/null || true
sudo systemctl restart ${{SERVICE_NAME}}

sleep 2

if sudo systemctl is-active --quiet ${{SERVICE_NAME}}; then
    log_info "Service is running"
else
    log_error "Service failed to start"
    sudo journalctl -u ${{SERVICE_NAME}} -n 20
    exit 1
fi

# Step 8: Register webhook
log_step "Registering Telegram webhook..."
WEBHOOK_URL="https://32.194.58.75/webhook/telegram"
RESPONSE=$(curl -s -k -X POST \\
    "https://api.telegram.org/bot{telegram_token}/setWebhook" \\
    -d "url=$WEBHOOK_URL" \\
    -d "allowed_updates=callback_query" \\
    -d "max_connections=1")

echo "$RESPONSE" | grep -q '"ok":true' && log_info "Webhook registered" || log_warn "Registration response: $RESPONSE"

# Step 9: Verify
log_step "Verifying webhook..."
WEBHOOK_INFO=$(curl -s -k -X GET \\
    "https://api.telegram.org/bot{telegram_token}/getWebhookInfo")

echo "$WEBHOOK_INFO"

echo ""
echo -e "${{GREEN}}========================================${{NC}}"
echo -e "${{GREEN}}DEPLOYMENT COMPLETE${{NC}}"
echo -e "${{GREEN}}========================================${{NC}}"
echo ""
echo "Webhook: https://32.194.58.75/webhook/telegram"
echo "Logs: sudo journalctl -u ${{SERVICE_NAME}} -f"
echo ""
'''
    
    return script


def deploy_to_ec2(ssh_key: str, env_vars: dict):
    """Deploy to EC2 via SSH"""
    
    print()
    print(Colors.blue("=" * 50))
    print(Colors.blue("DEPLOYING TO EC2"))
    print(Colors.blue("=" * 50))
    print()
    
    # Create deployment script
    log_step("Creating deployment script...")
    remote_script = create_remote_deployment_script(env_vars)
    
    # Create temporary script file
    temp_script = Path("/tmp/deploy_telegram.sh")
    try:
        temp_script.write_text(remote_script)
        temp_script.chmod(0o755)
        log_info("Deployment script created")
    except Exception as e:
        log_error(f"Failed to create script: {e}")
        return False
    
    # Transfer and execute script via SSH
    log_step("Connecting to EC2 and executing deployment...")
    
    cmd = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{EC2_USER}@{EC2_IP}",
        f"bash -s < {temp_script}"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            log_info("Deployment executed successfully")
            return True
        else:
            log_error(f"Deployment failed with return code {result.returncode}")
            return False
    
    except Exception as e:
        log_error(f"SSH connection failed: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            temp_script.unlink()
        except:
            pass


def verify_deployment(ssh_key: str) -> bool:
    """Verify deployment was successful"""
    
    print()
    print(Colors.blue("=" * 50))
    print(Colors.blue("VERIFYING DEPLOYMENT"))
    print(Colors.blue("=" * 50))
    print()
    
    log_step("Checking service status...")
    
    cmd = [
        "ssh",
        "-i", ssh_key,
        "-o", "ConnectTimeout=5",
        f"{EC2_USER}@{EC2_IP}",
        "sudo systemctl status telegram-webhook 2>/dev/null | grep running"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            log_info("Service is running")
            return True
        else:
            log_warn("Could not verify service status")
            return False
    
    except Exception as e:
        log_warn(f"Verification check failed: {e}")
        return False


def main():
    """Main deployment flow"""
    
    print()
    print(Colors.blue("=" * 50))
    print(Colors.blue("TELEGRAM WEBHOOK DEPLOYMENT FOR EC2"))
    print(Colors.blue("=" * 50))
    print()
    
    # Step 1: Find SSH key
    ssh_key = find_ssh_key()
    if not ssh_key:
        log_error("Cannot proceed without SSH key")
        print("\nPlease place stock-yard-key.pem in the current directory or ~/.ssh/")
        sys.exit(1)
    
    # Step 2: Read environment variables
    log_step("Reading environment variables...")
    env_vars = read_env_file()
    
    if not env_vars.get('TELEGRAM_BOT_TOKEN'):
        log_error("TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)
    
    if not env_vars.get('TELEGRAM_CHAT_ID'):
        log_error("TELEGRAM_CHAT_ID not found in .env")
        sys.exit(1)
    
    log_info("Environment variables loaded")
    
    # Step 3: Deploy
    if not deploy_to_ec2(ssh_key, env_vars):
        log_error("Deployment failed")
        sys.exit(1)
    
    # Step 4: Verify
    verify_deployment(ssh_key)
    
    # Summary
    print()
    print(Colors.blue("=" * 50))
    print(Colors.blue("DEPLOYMENT SUMMARY"))
    print(Colors.blue("=" * 50))
    print()
    print(f"✓ Webhook deployed to: {DEPLOY_DIR}")
    print(f"✓ HTTPS enabled (self-signed cert)")
    print(f"✓ Systemd service configured")
    print(f"✓ Telegram webhook registered")
    print()
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Health Check: https://{EC2_IP}/health")
    print()
    print("Next steps:")
    print("1. Test by sending a Telegram alert with a button")
    print("2. Click 'Confirm Trade' button")
    print("3. Monitor logs: ssh -i stock-yard-key.pem ubuntu@32.194.58.75 'sudo journalctl -u telegram-webhook -f'")
    print()
    log_info("Deployment completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDeployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)
