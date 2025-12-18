#!/bin/bash
# Startup script for Fly.io
# Start with dashboard only - trading system can be added later

set -e  # Exit on error for critical commands

# Create necessary directories
mkdir -p logs data/options_cache

# Log startup
echo "=========================================="
echo "TradeNova Starting..."
echo "=========================================="
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "=========================================="

# Start dashboard (foreground - Fly.io monitors this as main process)
echo "Starting dashboard on port 8501..."
exec streamlit run dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false
