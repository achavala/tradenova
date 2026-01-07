#!/usr/bin/env python3
"""Validate all tickers for options trading"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from alpaca_client import AlpacaClient

def main():
    print("="*60)
    print("TICKER CONFIGURATION UPDATED")
    print("="*60)
    print(f"\nTotal Tickers: {len(Config.TICKERS)}")
    print("\nTickers List:")
    for i, ticker in enumerate(Config.TICKERS, 1):
        print(f"  {i:2d}. {ticker}")

    print("\n" + "="*60)
    print("VALIDATING OPTIONS AVAILABILITY")
    print("="*60)

    client = AlpacaClient(paper=True)

    # Check if each ticker has options available
    valid_tickers = []
    invalid_tickers = []

    for ticker in Config.TICKERS:
        try:
            # Try to get asset info
            asset = client.api.get_asset(ticker)
            if asset.tradable:
                valid_tickers.append(ticker)
                print(f"  ✅ {ticker} - Tradable")
            else:
                invalid_tickers.append(ticker)
                print(f"  ❌ {ticker} - Not tradable")
        except Exception as e:
            invalid_tickers.append(ticker)
            print(f"  ❌ {ticker} - Error: {str(e)[:50]}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Valid tickers: {len(valid_tickers)}")
    print(f"  Invalid tickers: {len(invalid_tickers)}")

    if invalid_tickers:
        print(f"\n  ⚠️  Remove these: {', '.join(invalid_tickers)}")

    # Print current configuration
    print("\n" + "="*60)
    print("CURRENT RISK MANAGEMENT SETTINGS")
    print("="*60)
    print(f"  Stop Loss: -{Config.STOP_LOSS_PCT*100:.0f}%")
    print(f"  TP1: +{Config.TP1_PCT*100:.0f}% (exit {Config.TP1_EXIT_PCT*100:.0f}%)")
    print(f"  TP2: +{Config.TP2_PCT*100:.0f}% (exit {Config.TP2_EXIT_PCT*100:.0f}%)")
    print(f"  TP3: +{Config.TP3_PCT*100:.0f}% (exit {Config.TP3_EXIT_PCT*100:.0f}%)")
    print(f"  Max Contracts: {Config.MAX_CONTRACTS_PER_TRADE}")
    print(f"  Max Position: {Config.MAX_POSITION_PCT*100:.0f}%")
    print(f"  Max Portfolio Heat: {Config.MAX_PORTFOLIO_HEAT*100:.0f}%")
    print(f"  DTE Range: {Config.MIN_DTE}-{Config.MAX_DTE} days")

if __name__ == "__main__":
    main()

