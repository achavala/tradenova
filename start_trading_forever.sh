#!/bin/bash
# Start TradeNova and keep it running forever
# Auto-restarts on failure, runs in background

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Error: venv not found"
    exit 1
fi

# Create logs directory
mkdir -p logs

# PID file
PID_FILE="$SCRIPT_DIR/tradenova_forever.pid"

# Function to check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to stop
stop_trading() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Stopping TradeNova (PID: $PID)..."
            kill "$PID"
            wait "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    exit 0
}

# Trap signals
trap stop_trading SIGTERM SIGINT

# Check if already running
if is_running; then
    echo "⚠️  TradeNova is already running (PID: $(cat $PID_FILE))"
    exit 1
fi

echo "🚀 Starting TradeNova (will run forever, auto-restart on failure)..."
echo "   Press Ctrl+C to stop"
echo ""

# Main loop - restart on failure
RESTART_COUNT=0
MAX_RESTARTS=1000

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    echo "[$(date)] Starting TradeNova (attempt $((RESTART_COUNT + 1)))..."
    
    # Start in background
    nohup python tradenova_daemon.py --paper > logs/tradenova_forever.log 2>&1 &
    DAEMON_PID=$!
    
    echo $DAEMON_PID > "$PID_FILE"
    echo "   Started with PID: $DAEMON_PID"
    
    # Wait for process
    wait $DAEMON_PID
    EXIT_CODE=$?
    
    # Check if we should continue
    if [ ! -f "$PID_FILE" ]; then
        echo "[$(date)] PID file removed, stopping..."
        break
    fi
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Process exited normally"
        break
    else
        RESTART_COUNT=$((RESTART_COUNT + 1))
        echo "[$(date)] Process crashed (exit code: $EXIT_CODE), restarting in 5 seconds..."
        sleep 5
    fi
done

rm -f "$PID_FILE"
echo "[$(date)] TradeNova stopped"

