#!/bin/bash
##########################################################################
# Webhook Management Helper Script
# Easy commands to manage the Telegram webhook service on EC2
##########################################################################

EC2_IP="32.194.58.75"
EC2_USER="ubuntu"
SSH_KEY="${SSH_KEY:-stock-yard-key.pem}"
SERVICE="telegram-webhook"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_step() { echo -e "${BLUE}→${NC} $1"; }

# Find SSH key
find_ssh_key() {
    if [ -f "$SSH_KEY" ]; then
        return 0
    fi
    
    if [ -f ~/.ssh/$SSH_KEY ]; then
        SSH_KEY=~/.ssh/$SSH_KEY
        return 0
    fi
    
    log_error "SSH key not found: $SSH_KEY"
    return 1
}

# Display usage
usage() {
    cat << EOF
${BLUE}TELEGRAM WEBHOOK MANAGEMENT${NC}

Usage: $0 [command]

Commands:
  status      - Check service status
  restart     - Restart service
  stop        - Stop service
  start       - Start service
  logs        - Follow service logs in real-time
  logs N      - Show last N lines of logs
  ssh         - SSH into EC2
  health      - Test health endpoint
  webhook-info - Get Telegram webhook info
  
Examples:
  $0 status
  $0 logs
  $0 logs 50
  $0 ssh
  $0 health

EOF
}

# SSH into EC2
ssh_into_ec2() {
    log_step "Connecting to EC2..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP"
}

# Check service status
service_status() {
    log_step "Checking service status..."
    ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_IP" \
        "sudo systemctl status $SERVICE"
}

# Restart service
restart_service() {
    log_step "Restarting service..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" \
        "sudo systemctl restart $SERVICE && echo 'Service restarted'" || \
        log_error "Failed to restart service"
}

# Stop service
stop_service() {
    log_step "Stopping service..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" \
        "sudo systemctl stop $SERVICE && echo 'Service stopped'" || \
        log_error "Failed to stop service"
}

# Start service
start_service() {
    log_step "Starting service..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" \
        "sudo systemctl start $SERVICE && echo 'Service started'" || \
        log_error "Failed to start service"
}

# Follow logs
follow_logs() {
    log_step "Following logs (Ctrl+C to exit)..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" \
        "sudo journalctl -u $SERVICE -f"
}

# Show last N logs
show_logs() {
    local lines=${1:-20}
    log_step "Last $lines lines of logs..."
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" \
        "sudo journalctl -u $SERVICE -n $lines --no-pager"
}

# Test health endpoint
test_health() {
    log_step "Testing health endpoint..."
    curl -s -k "https://$EC2_IP/health" | python -m json.tool || \
        log_error "Health check failed"
}

# Get Telegram webhook info
get_webhook_info() {
    local token=$(grep TELEGRAM_BOT_TOKEN .env 2>/dev/null | cut -d'=' -f2)
    
    if [ -z "$token" ]; then
        log_error "TELEGRAM_BOT_TOKEN not found in .env"
        return 1
    fi
    
    log_step "Getting Telegram webhook info..."
    curl -s -k -X GET \
        "https://api.telegram.org/bot$token/getWebhookInfo" | python -m json.tool || \
        log_error "Failed to get webhook info"
}

# Main
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    # Find SSH key
    find_ssh_key || exit 1
    
    log_info "Using SSH key: $SSH_KEY"
    log_info "Target: $EC2_USER@$EC2_IP"
    
    command=$1
    shift
    
    case "$command" in
        status)
            service_status
            ;;
        restart)
            restart_service
            ;;
        stop)
            stop_service
            ;;
        start)
            start_service
            ;;
        logs)
            if [ -z "$1" ]; then
                follow_logs
            else
                show_logs "$1"
            fi
            ;;
        ssh)
            ssh_into_ec2
            ;;
        health)
            test_health
            ;;
        webhook-info)
            get_webhook_info
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
