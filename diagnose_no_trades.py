#!/usr/bin/env python3
"""
Diagnose why no trades are being executed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnose():
    """Diagnose why no trades are executing"""
    print("="*70)
    print("DIAGNOSING WHY NO TRADES ARE EXECUTING")
    print("="*70)
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    trader = IntegratedTrader(dry_run=False, paper_trading=True)
    
    print(f"\n1. CONFIGURED TICKERS: {len(Config.TICKERS)}")
    print(f"   {', '.join(Config.TICKERS)}")
    
    print(f"\n2. MARKET STATUS:")
    is_open = client.is_market_open()
    print(f"   Market Open: {is_open}")
    
    print(f"\n3. ACCOUNT STATUS:")
    account = client.get_account()
    print(f"   Equity: ${account['equity']:,.2f}")
    print(f"   Buying Power: ${account['buying_power']:,.2f}")
    print(f"   Trading Blocked: {account.get('trading_blocked', False)}")
    
    print(f"\n4. CURRENT POSITIONS:")
    positions = client.get_positions()
    print(f"   Active Positions: {len(positions)}")
    for pos in positions:
        print(f"     - {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
    
    print(f"\n5. TESTING SIGNAL GENERATION:")
    print(f"   Testing first 3 tickers for signals...")
    
    orchestrator = MultiAgentOrchestrator(client)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    signals_found = 0
    for ticker in Config.TICKERS[:3]:
        try:
            bars = client.get_historical_bars(ticker, TimeFrame.Day, start_date, end_date)
            
            if bars.empty or len(bars) < 50:
                print(f"   ⚠️  {ticker}: Insufficient data ({len(bars)} bars)")
                continue
            
            intent = orchestrator.analyze_symbol(ticker, bars)
            
            if intent:
                print(f"   ✅ {ticker}: {intent.direction.value} signal (confidence: {intent.confidence:.2%}, agent: {intent.agent_name})")
                if intent.confidence >= 0.5:
                    signals_found += 1
                    print(f"      → Would execute (confidence >= 50%)")
                else:
                    print(f"      → Would NOT execute (confidence {intent.confidence:.2%} < 50%)")
            else:
                print(f"   ⏸️  {ticker}: No signal generated")
                
        except Exception as e:
            print(f"   ❌ {ticker}: Error - {e}")
    
    print(f"\n6. CONFIDENCE THRESHOLD:")
    print(f"   Required: >= 50% (0.5)")
    print(f"   Signals found with >= 50%: {signals_found}/3")
    
    print(f"\n7. RISK MANAGER STATUS:")
    risk_status = trader.risk_manager.get_risk_status()
    print(f"   Risk Level: {risk_status['risk_level']}")
    print(f"   Can Trade: {risk_status.get('can_trade', 'Unknown')}")
    print(f"   Daily P&L: ${risk_status.get('daily_pnl', 0):.2f}")
    
    print(f"\n8. SUMMARY:")
    if not is_open:
        print("   ❌ Market is CLOSED - No trades will execute")
    elif account.get('trading_blocked', False):
        print("   ❌ Trading is BLOCKED on account")
    elif signals_found == 0:
        print("   ⚠️  No signals with confidence >= 50% found")
        print("   → This is normal - system waits for high-confidence setups")
        print("   → Lower confidence threshold in integrated_trader.py if needed")
    else:
        print(f"   ✅ {signals_found} signals found with sufficient confidence")
        print("   → Trades should execute if risk manager allows")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    diagnose()

