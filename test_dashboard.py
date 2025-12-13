#!/usr/bin/env python3
"""
Quick test script to verify dashboard imports work
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing dashboard imports...")
    
    # Test basic imports
    import streamlit as st
    print("✅ Streamlit imported")
    
    import pandas as pd
    print("✅ Pandas imported")
    
    import plotly.graph_objects as go
    import plotly.express as px
    print("✅ Plotly imported")
    
    # Test TradeNova imports
    from logs.metrics_tracker import MetricsTracker
    print("✅ MetricsTracker imported")
    
    from config import Config
    print("✅ Config imported")
    
    from alpaca_client import AlpacaClient
    print("✅ AlpacaClient imported")
    
    # Test metrics calculation
    tracker = MetricsTracker()
    metrics = tracker.calculate_metrics()
    print(f"✅ Metrics calculated: {len(metrics)} fields")
    
    # Test dashboard module
    print("\n✅ All imports successful!")
    print("\nTo start the dashboard, run:")
    print("  streamlit run dashboard.py --server.port 8502")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

