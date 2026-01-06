#!/bin/bash
#
# Fix Trading Authentication Issue
# Restarts trading system with proper environment variables
#

cd "$(dirname "$0")/.." || exit 1

echo "🔧 Fixing Trading Authentication Issue"
echo ""

# Stop all running trading processes
echo "1️⃣ Stopping existing trading processes..."
pkill -f run_daily.py
sleep 2

# Verify they're stopped
if pgrep -f run_daily.py > /dev/null; then
    echo "⚠️  Some processes still running, forcing kill..."
    pkill -9 -f run_daily.py
    sleep 1
fi

echo "✅ All trading processes stopped"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "   Please create .env file with ALPACA_API_KEY and ALPACA_SECRET_KEY"
    exit 1
fi

echo "2️⃣ Verifying environment variables..."
source .env 2>/dev/null || true

if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
    echo "⚠️  WARNING: Environment variables not set in .env"
    echo "   Checking if they're loaded from .env file..."
    
    # Try to load from .env manually
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
    echo "❌ ERROR: ALPACA_API_KEY or ALPACA_SECRET_KEY not set!"
    echo "   Please check your .env file"
    exit 1
fi

echo "✅ Environment variables found"
echo ""

# Activate virtual environment
echo "3️⃣ Activating virtual environment..."
if [ ! -d venv ]; then
    echo "❌ ERROR: venv directory not found!"
    echo "   Please create virtual environment: python -m venv venv"
    exit 1
fi

source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""

# Test API connection
echo "4️⃣ Testing Alpaca API connection..."
python -c "
from config import Config
from alpaca_client import AlpacaClient

try:
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    account = client.get_account()
    print('✅ API connection successful!')
    print(f'   Account Equity: \${float(account[\"equity\"]):,.2f}')
except Exception as e:
    print(f'❌ API connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ API connection test failed. Please check your credentials."
    exit 1
fi

echo ""
echo "5️⃣ Starting trading system..."
echo ""

# Start trading system in background with proper environment
nohup python run_daily.py --paper > logs/trading_restart.log 2>&1 &
TRADING_PID=$!

sleep 3

# Check if process is running
if ps -p $TRADING_PID > /dev/null; then
    echo "✅ Trading system started successfully!"
    echo "   PID: $TRADING_PID"
    echo "   Log: logs/trading_restart.log"
    echo ""
    echo "📋 Monitor with:"
    echo "   tail -f logs/trading_restart.log"
    echo "   tail -f logs/trading_today.log"
    echo ""
    echo "🔍 Check status with:"
    echo "   python scripts/validate_trades_today.py"
else
    echo "❌ Trading system failed to start!"
    echo "   Check logs/trading_restart.log for errors"
    exit 1
fi





