#!/usr/bin/env python3
"""
Comprehensive Diagnostic Script for No Trades Issue
Analyzes why trades are not being executed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator
# Risk management imports (check what exists)
try:
    from core.risk.portfolio_risk_manager import PortfolioRiskManager
    HAS_PORTFOLIO_RISK = True
except ImportError:
    HAS_PORTFOLIO_RISK = False

try:
    from core.risk.portfolio_greeks import PortfolioGreeksAggregator
    HAS_GREEKS = True
except ImportError:
    HAS_GREEKS = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("="*80)
    print("COMPREHENSIVE TRADE DIAGNOSTIC ANALYSIS")
    print("="*80)
    print(f"Analysis Time: {datetime.now()}\n")
    
    # 1. System Status
    print("="*80)
    print("1. SYSTEM STATUS")
    print("="*80)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        is_open = client.is_market_open()
        account = client.get_account()
        positions = client.get_positions()
        orders = client.get_orders(status='all', limit=20)
        
        print(f"✅ Market Status: {'OPEN' if is_open else 'CLOSED'}")
        print(f"✅ Account Equity: ${float(account['equity']):,.2f}")
        print(f"✅ Buying Power: ${float(account['buying_power']):,.2f}")
        print(f"✅ Open Positions: {len(positions)}")
        print(f"✅ Recent Orders: {len(orders)}")
        
        if not is_open:
            print("\n⚠️  MARKET IS CLOSED - No trades will execute")
            return
        
    except Exception as e:
        print(f"❌ Error checking system status: {e}")
        return
    
    # 2. Configuration Check
    print("\n" + "="*80)
    print("2. CONFIGURATION")
    print("="*80)
    print(f"✅ Tickers: {Config.TICKERS}")
    print(f"✅ Max Active Trades: {Config.MAX_ACTIVE_TRADES}")
    print(f"✅ Position Size %: {Config.POSITION_SIZE_PCT*100}%")
    print(f"✅ DTE Range: {Config.MIN_DTE}-{Config.MAX_DTE} days")
    print(f"✅ SPY Excluded: {'SPY' not in Config.TICKERS}")
    
    # 3. Signal Generation Analysis
    print("\n" + "="*80)
    print("3. SIGNAL GENERATION ANALYSIS")
    print("="*80)
    
    try:
        orchestrator = MultiAgentOrchestrator(client)
        
        signals_found = []
        signals_rejected = []
        no_data_symbols = []
        low_confidence_symbols = []
        
        for symbol in Config.TICKERS[:5]:  # Test first 5 for speed
            print(f"\n--- Analyzing {symbol} ---")
            
            try:
                # Get historical data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                bars = client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
                
                if bars.empty or len(bars) < 50:
                    print(f"  ❌ Insufficient data: {len(bars)} bars (need 50+)")
                    no_data_symbols.append(symbol)
                    continue
                
                print(f"  ✅ Data: {len(bars)} bars available")
                
                # Analyze symbol
                trade_intent = orchestrator.analyze_symbol(symbol, bars)
                
                if trade_intent is None:
                    print(f"  ⚠️  No trade intent generated")
                    low_confidence_symbols.append(symbol)
                    continue
                
                direction = trade_intent.direction.value
                confidence = trade_intent.confidence
                agent = trade_intent.agent_name
                reasoning = trade_intent.reasoning[:100] if trade_intent.reasoning else "N/A"
                
                print(f"  ✅ Signal Generated:")
                print(f"     Direction: {direction}")
                print(f"     Confidence: {confidence:.2%}")
                print(f"     Agent: {agent}")
                print(f"     Reasoning: {reasoning}")
                
                # Check confidence threshold
                if confidence < 0.20:  # Backtest threshold
                    print(f"  ⚠️  REJECTED: Confidence {confidence:.2%} < 0.20 threshold")
                    signals_rejected.append({
                        'symbol': symbol,
                        'reason': f'Low confidence ({confidence:.2%} < 0.20)',
                        'confidence': confidence,
                        'agent': agent
                    })
                else:
                    print(f"  ✅ PASSED: Confidence {confidence:.2%} >= 0.20 threshold")
                    signals_found.append({
                        'symbol': symbol,
                        'direction': direction,
                        'confidence': confidence,
                        'agent': agent,
                        'reasoning': reasoning
                    })
                
            except Exception as e:
                print(f"  ❌ Error analyzing {symbol}: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print("\n" + "-"*80)
        print("SIGNAL GENERATION SUMMARY:")
        print(f"  ✅ Signals Found: {len(signals_found)}")
        print(f"  ⚠️  Signals Rejected (Low Confidence): {len(signals_rejected)}")
        print(f"  ❌ No Data: {len(no_data_symbols)}")
        print(f"  ⚠️  Low Confidence/No Intent: {len(low_confidence_symbols)}")
        
        if signals_found:
            print("\n  SIGNALS THAT PASSED:")
            for sig in signals_found:
                print(f"    - {sig['symbol']}: {sig['direction']} @ {sig['confidence']:.2%} ({sig['agent']})")
        
        if signals_rejected:
            print("\n  SIGNALS REJECTED (Low Confidence):")
            for sig in signals_rejected:
                print(f"    - {sig['symbol']}: {sig['reason']} ({sig['agent']})")
        
    except Exception as e:
        print(f"❌ Error in signal generation analysis: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Risk Management Check
    print("\n" + "="*80)
    print("4. RISK MANAGEMENT CHECK")
    print("="*80)
    
    can_trade = True  # Default
    try:
        if HAS_PORTFOLIO_RISK and HAS_GREEKS:
            risk_manager = PortfolioRiskManager()
            greeks_aggregator = PortfolioGreeksAggregator(client)
            
            # Get current portfolio state
            portfolio_greeks = greeks_aggregator.get_portfolio_greeks(positions)
            
            print(f"Portfolio Greeks:")
            print(f"  Net Delta: {portfolio_greeks.get('net_delta', 0):.2f}")
            print(f"  Net Gamma: {portfolio_greeks.get('net_gamma', 0):.2f}")
            print(f"  Net Theta: {portfolio_greeks.get('net_theta', 0):.2f}")
            print(f"  Net Vega: {portfolio_greeks.get('net_vega', 0):.2f}")
            
            # Check if we can open new positions
            can_trade, reason = risk_manager.can_open_new_position(portfolio_greeks)
            
            if can_trade:
                print(f"\n✅ Risk Check: ALLOWED to open new positions")
            else:
                print(f"\n❌ Risk Check: BLOCKED - {reason}")
            
            # Check limits
            print(f"\nRisk Limits:")
            print(f"  Max Delta: ±{risk_manager.MAX_DELTA}")
            print(f"  Max Theta: {risk_manager.MAX_THETA_PER_DAY}/day")
            print(f"  Max Gamma: ±{risk_manager.MAX_GAMMA}")
            print(f"  Max Vega: ±{risk_manager.MAX_VEGA}")
        else:
            print("⚠️  Portfolio risk management modules not available")
            print("   Using basic risk checks only")
        
    except Exception as e:
        print(f"❌ Error in risk management check: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Position Limits Check
    print("\n" + "="*80)
    print("5. POSITION LIMITS CHECK")
    print("="*80)
    
    current_positions = len(positions)
    max_positions = Config.MAX_ACTIVE_TRADES
    
    print(f"Current Positions: {current_positions}")
    print(f"Max Positions: {max_positions}")
    
    if current_positions >= max_positions:
        print(f"❌ BLOCKED: Max positions reached ({current_positions}/{max_positions})")
    else:
        print(f"✅ ALLOWED: Can open {max_positions - current_positions} more positions")
    
    # 6. Recommendations
    print("\n" + "="*80)
    print("6. RECOMMENDATIONS")
    print("="*80)
    
    recommendations = []
    
    if len(signals_found) == 0:
        recommendations.append("⚠️  No signals passing confidence threshold (0.20)")
        recommendations.append("   → Consider lowering confidence threshold in backtest_trading.py")
        recommendations.append("   → Check if market conditions are suitable for trading")
    
    if len(signals_rejected) > 0:
        recommendations.append(f"⚠️  {len(signals_rejected)} signals rejected due to low confidence")
        recommendations.append("   → Signals are being generated but confidence is too low")
        recommendations.append("   → Current threshold: 0.20 (20%)")
    
    if len(no_data_symbols) > 0:
        recommendations.append(f"⚠️  {len(no_data_symbols)} symbols have insufficient data")
        recommendations.append("   → Ensure historical data is available")
    
    if not can_trade:
        recommendations.append("❌ Risk management is blocking trades")
        recommendations.append("   → Check portfolio Greeks limits")
    
    if current_positions >= max_positions:
        recommendations.append("❌ Max positions reached - no new trades allowed")
    
    if len(recommendations) == 0:
        recommendations.append("✅ System appears healthy - no obvious issues found")
        recommendations.append("   → Market conditions may not be suitable for trading")
        recommendations.append("   → Wait for better setups or adjust strategy parameters")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

