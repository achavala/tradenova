#!/bin/bash
#
# TradeNova Monitoring Setup Script
# Sets up LaunchAgents for trading daemon and watchdog
#

set -e

echo "=============================================="
echo "TradeNova Monitoring Setup"
echo "=============================================="
echo ""

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PROJECT_DIR="$HOME/TradeNova"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"
print_status "Logs directory ready"

# Stop any existing services
echo ""
echo "Stopping existing services..."

if launchctl list | grep -q "com.tradenova.trading"; then
    launchctl unload "$LAUNCH_AGENTS_DIR/com.tradenova.trading.plist" 2>/dev/null || true
    print_status "Stopped trading daemon"
fi

if launchctl list | grep -q "com.tradenova.watchdog"; then
    launchctl unload "$LAUNCH_AGENTS_DIR/com.tradenova.watchdog.plist" 2>/dev/null || true
    print_status "Stopped watchdog"
fi

sleep 2

# Copy plist files to LaunchAgents
echo ""
echo "Installing LaunchAgents..."

# Trading daemon
if [ -f "$PROJECT_DIR/com.tradenova.trading.plist" ]; then
    cp "$PROJECT_DIR/com.tradenova.trading.plist" "$LAUNCH_AGENTS_DIR/"
    print_status "Copied trading daemon plist"
elif [ -f "$LAUNCH_AGENTS_DIR/com.tradenova.trading.plist" ]; then
    print_status "Trading daemon plist already installed"
else
    print_error "Trading daemon plist not found!"
fi

# Watchdog
if [ -f "$LAUNCH_AGENTS_DIR/com.tradenova.watchdog.plist" ]; then
    print_status "Watchdog plist already installed"
else
    print_warning "Watchdog plist not found in LaunchAgents"
fi

# Load services
echo ""
echo "Starting services..."

# Load trading daemon
launchctl load "$LAUNCH_AGENTS_DIR/com.tradenova.trading.plist" 2>/dev/null || true
if launchctl list | grep -q "com.tradenova.trading"; then
    print_status "Trading daemon loaded"
else
    print_warning "Trading daemon may not have started (check logs)"
fi

# Load watchdog if exists
if [ -f "$LAUNCH_AGENTS_DIR/com.tradenova.watchdog.plist" ]; then
    launchctl load "$LAUNCH_AGENTS_DIR/com.tradenova.watchdog.plist" 2>/dev/null || true
    if launchctl list | grep -q "com.tradenova.watchdog"; then
        print_status "Watchdog loaded"
    else
        print_warning "Watchdog may not have started (check logs)"
    fi
fi

# Verify services
echo ""
echo "=============================================="
echo "Service Status"
echo "=============================================="

echo ""
echo "LaunchAgents:"
launchctl list | grep tradenova || print_warning "No TradeNova services found"

echo ""
echo "Processes:"
ps aux | grep -E "run_daily|watchdog" | grep -v grep || print_warning "No TradeNova processes running"

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Check logs: tail -f $PROJECT_DIR/logs/trading_automation.error.log"
echo "2. Check watchdog: tail -f $PROJECT_DIR/logs/watchdog.log"
echo "3. Configure alerts: Edit $PROJECT_DIR/.env with email settings"
echo "4. Test alerts: cd $PROJECT_DIR && python scripts/watchdog.py --test-alert"
echo ""


