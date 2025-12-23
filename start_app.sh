#!/bin/bash
# Startup script for Fly.io - runs both dashboard and trading system

set -e

echo "Starting TradeNova on Fly.io..."

# Set timezone to America/New_York for market hours
export TZ=America/New_York

# Create logs directory if it doesn't exist
mkdir -p logs

# Start trading system in background
echo "Starting trading system..."
python run_daily.py --paper &
TRADING_PID=$!

# Wait a moment for trading system to initialize
sleep 2

# Start Streamlit dashboard in foreground (so Fly.io monitors it)
echo "Starting Streamlit dashboard..."
exec streamlit run dashboard.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false

# If Streamlit exits, kill trading system
trap "kill $TRADING_PID 2>/dev/null || true" EXIT

