#!/bin/bash
# Install TradeNova as a macOS Launch Agent
# This will make it run automatically on boot and restart on failure

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PLIST_FILE="com.tradenova.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo "="*70
echo "INSTALLING TRADENOVA AS AUTOMATIC SERVICE"
echo "="*70
echo ""

# Check if plist exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "❌ Error: $PLIST_FILE not found"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Update paths in plist file
echo "📝 Updating paths in plist file..."
sed -i.bak "s|/Users/chavala/TradeNova|$SCRIPT_DIR|g" "$PLIST_FILE"

# Copy plist to LaunchAgents
echo "📋 Copying plist to LaunchAgents..."
cp "$PLIST_FILE" "$TARGET_PLIST"

# Load the service
echo "🚀 Loading service..."
launchctl unload "$TARGET_PLIST" 2>/dev/null  # Unload if already loaded
launchctl load "$TARGET_PLIST"

# Check status
if launchctl list | grep -q "com.tradenova"; then
    echo ""
    echo "✅ Service installed and started successfully!"
    echo ""
    echo "Service Status:"
    launchctl list | grep "com.tradenova"
    echo ""
    echo "To manage the service:"
    echo "  Start:   launchctl start com.tradenova"
    echo "  Stop:    launchctl stop com.tradenova"
    echo "  Restart: launchctl unload $TARGET_PLIST && launchctl load $TARGET_PLIST"
    echo "  Status:  launchctl list | grep com.tradenova"
    echo "  Logs:    tail -f $SCRIPT_DIR/logs/tradenova_service.log"
    echo ""
else
    echo "⚠️  Service may not have started. Check logs:"
    echo "   tail -f $SCRIPT_DIR/logs/tradenova_service_error.log"
fi

echo "="*70

