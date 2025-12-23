#!/usr/bin/env python3
"""
Check Today's Trading Activity
Analyzes signals, trades, and rejections for today
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, date, timedelta
from alpaca_client import AlpacaClient
from core.live.integrated_trader import IntegratedTrader
from core.risk.advanced_risk_manager import AdvancedRiskManager
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from services.iv_rank_service import IVRankService
from config import Config
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

def check_today_trades():
    """Check today's trading activity"""
    
    print("="*80)
    print("TODAY'S TRADING ACTIVITY ANALYSIS")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Check account
    try:
        account = client.get_account()
        print("ACCOUNT STATUS:")
        print("-" * 80)
        print(f"Equity: ${float(account['equity']):,.2f}")
        print(f"Cash: ${float(account['cash']):,.2f}")
        print()
    except Exception as e:
        print(f"❌ Error getting account: {e}")
        return False
    
    # Check positions
    positions = client.get_positions()
    print(f"CURRENT POSITIONS: {len(positions)}")
    print("-" * 80)
    if positions:
        for pos in positions:
            print(f"{pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
            print(f"  P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']:.2%})")
    else:
        print("  No open positions")
    print()
    
    # Check market status
    try:
        clock = client.api.get_clock()
        is_open = clock.is_open
        print(f"MARKET STATUS: {'✅ OPEN' if is_open else '❌ CLOSED'}")
        if not is_open:
            print(f"Next Open: {clock.next_open}")
        print()
    except Exception as e:
        print(f"⚠️  Could not check market status: {e}\n")
    
    # Initialize trader for analysis
    try:
        trader = IntegratedTrader(dry_run=True, paper_trading=True)
        print("✅ Trading system initialized\n")
    except Exception as e:
        print(f"❌ Error initializing trader: {e}\n")
        return False
    
    # Check risk status
    risk_status = trader.risk_manager.get_risk_status()
    print("RISK STATUS:")
    print("-" * 80)
    print(f"Risk Level: {risk_status['risk_level']}")
    print(f"Daily P&L: ${risk_status['daily_pnl']:,.2f}")
    print(f"Drawdown: {risk_status['drawdown']:.2%}")
    print()
    
    # Analyze signals for all tickers
    print("SIGNAL GENERATION ANALYSIS:")
    print("-" * 80)
    
    signals_found = []
    signals_rejected = []
    no_signals = []
    
    iv_service = IVRankService()
    
    for symbol in Config.TICKERS:
        try:
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            bars = client.get_historical_bars(
                symbol, TimeFrame.Day, start_date, end_date
            )
            
            if bars.empty or len(bars) < 50:
                no_signals.append((symbol, "Insufficient data"))
                continue
            
            # Get signal
            intent = trader.orchestrator.analyze_symbol(symbol, bars)
            
            if not intent or intent.direction.value == 'FLAT':
                no_signals.append((symbol, "No signal generated"))
                continue
            
            # Signal found - check risk
            current_price = client.get_latest_price(symbol)
            if not current_price:
                signals_rejected.append((symbol, "Could not get current price"))
                continue
            
            # Get IV Rank
            metrics = iv_service.get_iv_metrics(symbol)
            iv_rank = metrics.get('iv_rank')
            
            # Check all risk layers
            side = 'buy' if intent.direction.value == 'LONG' else 'sell'
            
            # Get current positions for UVaR
            current_positions = []
            for pos in positions:
                current_positions.append({
                    'symbol': pos['symbol'],
                    'qty': float(pos['qty']),
                    'entry_price': pos.get('avg_entry_price', 0),
                    'current_price': pos.get('current_price', 0)
                })
            
            # Check trade allowance
            allowed, reason, risk_level = trader.risk_manager.check_trade_allowed(
                symbol=symbol,
                qty=100,
                price=current_price,
                side=side,
                iv_rank=iv_rank,
                current_positions=current_positions
            )
            
            signal_info = {
                'symbol': symbol,
                'direction': intent.direction.value,
                'confidence': intent.confidence,
                'agent': intent.agent_name,
                'price': current_price,
                'iv_rank': iv_rank,
                'allowed': allowed,
                'reason': reason
            }
            
            if allowed:
                signals_found.append(signal_info)
            else:
                signals_rejected.append((symbol, reason))
            
        except Exception as e:
            signals_rejected.append((symbol, f"Error: {e}"))
    
    # Summary
    print(f"\nSIGNALS FOUND: {len(signals_found)}")
    if signals_found:
        for sig in signals_found:
            print(f"  ✅ {sig['symbol']}: {sig['direction']} @ {sig['confidence']:.2%} ({sig['agent']})")
            print(f"     Price: ${sig['price']:.2f}, IV Rank: {sig['iv_rank']:.1f}%" if sig['iv_rank'] else f"     Price: ${sig['price']:.2f}, IV Rank: N/A")
            print(f"     Status: ✅ ALLOWED")
    
    print(f"\nSIGNALS REJECTED: {len(signals_rejected)}")
    if signals_rejected:
        for symbol, reason in signals_rejected:
            print(f"  ❌ {symbol}: {reason}")
    
    print(f"\nNO SIGNALS: {len(no_signals)}")
    if no_signals:
        for symbol, reason in no_signals[:5]:
            print(f"  ⚠️  {symbol}: {reason}")
        if len(no_signals) > 5:
            print(f"  ... and {len(no_signals) - 5} more")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Tickers Analyzed: {len(Config.TICKERS)}")
    print(f"Signals Generated: {len(signals_found) + len(signals_rejected)}")
    print(f"  ✅ Allowed: {len(signals_found)}")
    print(f"  ❌ Rejected: {len(signals_rejected)}")
    print(f"  ⚠️  No Signal: {len(no_signals)}")
    print()
    
    if len(signals_found) > 0:
        print("✅ TRADES AVAILABLE:")
        print("   The system found signals that passed all risk checks.")
        print("   These should be executed by the trading system.")
    elif len(signals_rejected) > 0:
        print("⚠️  SIGNALS REJECTED:")
        print("   Signals were generated but blocked by risk management.")
        print("   Check rejection reasons above.")
    else:
        print("⚠️  NO SIGNALS:")
        print("   No trading signals generated for any ticker.")
        print("   This could be due to market conditions or strategy parameters.")
    
    return True

if __name__ == "__main__":
    success = check_today_trades()
    sys.exit(0 if success else 1)

