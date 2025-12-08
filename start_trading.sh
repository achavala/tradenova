#!/bin/bash
# TradeNova Trading Starter Script
# Automatically activates venv and starts trading

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Error: venv directory not found"
    echo "   Please run: python3 -m venv venv"
    exit 1
fi

# Check if pandas is installed
if ! python -c "import pandas" 2>/dev/null; then
    echo "⚠️  Warning: pandas not found, installing..."
    pip install pandas --quiet
fi

# Check for required arguments
PAPER_FLAG=""
DRY_RUN_FLAG=""
SHADOW_FLAG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --paper)
            PAPER_FLAG="--paper"
            shift
            ;;
        --dry-run)
            DRY_RUN_FLAG="--dry-run"
            shift
            ;;
        --shadow)
            SHADOW_FLAG="--shadow"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./start_trading.sh [--paper] [--dry-run] [--shadow]"
            exit 1
            ;;
    esac
done

# Default to paper trading if no mode specified
if [ -z "$PAPER_FLAG" ] && [ -z "$DRY_RUN_FLAG" ] && [ -z "$SHADOW_FLAG" ]; then
    PAPER_FLAG="--paper"
    echo "ℹ️  Defaulting to paper trading mode"
fi

echo ""
echo "🚀 Starting TradeNova Trading System..."
echo ""

# Build command
CMD="python run_daily.py"
if [ -n "$PAPER_FLAG" ]; then
    CMD="$CMD $PAPER_FLAG"
fi
if [ -n "$DRY_RUN_FLAG" ]; then
    CMD="$CMD $DRY_RUN_FLAG"
fi
if [ -n "$SHADOW_FLAG" ]; then
    CMD="$CMD $SHADOW_FLAG"
fi

echo "Command: $CMD"
echo ""
echo "Press CTRL+C to stop"
echo ""

# Run the command
exec $CMD

