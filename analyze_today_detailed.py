#!/usr/bin/env python
"""
Detailed Trade Analysis Script
Analyzes all trades from today with reasoning for signals, rejections, and execution
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from alpaca_client import AlpacaClient
from config import Config

def parse_log_file(log_path: str):
    """Parse the trading log file for signal analysis"""
    signals = []
    rejections = []
    executions = []
    errors = []
    
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Parse timestamp
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            timestamp = timestamp_match.group(1) if timestamp_match else None
            
            # Signal found
            if 'Signal found for' in line:
                match = re.search(r'Signal found for (\w+): (\w+) @ ([\d.]+)% \((\w+)\)', line)
                if match:
                    signals.append({
                        'timestamp': timestamp,
                        'symbol': match.group(1),
                        'direction': match.group(2),
                        'confidence': float(match.group(3)),
                        'agent': match.group(4)
                    })
            
            # Trade execution
            if 'EXECUTING TRADE' in line:
                match = re.search(r'EXECUTING TRADE: (\w+) (\w+) \(confidence: ([\d.]+)%, agent: (\w+)\)', line)
                if match:
                    executions.append({
                        'timestamp': timestamp,
                        'symbol': match.group(1),
                        'direction': match.group(2),
                        'confidence': float(match.group(3)),
                        'agent': match.group(4)
                    })
            
            # Options order placed
            if 'Options order placed' in line:
                match = re.search(r'Options order placed: (\w+) (\d+) (\w+) @ (\w+)', line)
                if match:
                    executions.append({
                        'timestamp': timestamp,
                        'type': 'options_order',
                        'side': match.group(1),
                        'qty': int(match.group(2)),
                        'symbol': match.group(3),
                        'order_type': match.group(4)
                    })
            
            # Rejections
            if 'rejected' in line.lower() or 'skipping' in line.lower() or 'blocked' in line.lower():
                rejections.append({
                    'timestamp': timestamp,
                    'reason': line.strip()
                })
            
            # Position size warnings
            if 'Position size too small' in line:
                match = re.search(r'Position size too small for (\w+)', line)
                if match:
                    rejections.append({
                        'timestamp': timestamp,
                        'symbol': match.group(1),
                        'reason': 'Position size too small - insufficient capital for 1 contract'
                    })
            
            # Errors
            if 'ERROR' in line or 'Error' in line:
                errors.append({
                    'timestamp': timestamp,
                    'error': line.strip()
                })
                
            # Final intent from multi-agent
            if 'Final intent' in line:
                match = re.search(r'(\w+): Final intent - (\w+) \(confidence: ([\d.]+), agent: (\w+)\)', line)
                if match:
                    signals.append({
                        'timestamp': timestamp,
                        'symbol': match.group(1),
                        'direction': match.group(2),
                        'confidence': float(match.group(3)) * 100,  # Convert to percentage
                        'agent': match.group(4),
                        'type': 'multi_agent_final'
                    })
    
    except Exception as e:
        print(f"Error parsing log: {e}")
    
    return signals, rejections, executions, errors

def analyze_positions(client):
    """Analyze current positions with detailed breakdown"""
    positions = client.get_positions()
    analysis = []
    
    for pos in positions:
        symbol = pos['symbol']
        qty = float(pos['qty'])
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        unrealized = float(pos['unrealized_pl'])
        unrealized_pct = float(pos['unrealized_plpc']) * 100
        cost_basis = float(pos['cost_basis'])
        market_value = float(pos['market_value'])
        
        # Parse option details
        is_option = len(symbol) > 10
        option_details = {}
        
        if is_option:
            # Parse OCC option symbol format: UNDERLYING + YYMMDD + C/P + STRIKE
            # Find where digits start (expiration date)
            import re
            match = re.match(r'^([A-Z]+)(\d{6})([CP])(\d+)$', symbol)
            if match:
                underlying = match.group(1)
                exp_str = match.group(2)
                option_type = match.group(3)
                strike_str = match.group(4)
                
                try:
                    exp_date = datetime.strptime(f"20{exp_str}", "%Y%m%d")
                    days_to_exp = (exp_date - datetime.now()).days
                except:
                    exp_date = datetime.now() + timedelta(days=7)
                    days_to_exp = 7
                
                strike = float(strike_str) / 1000
                
                option_details = {
                    'underlying': underlying,
                    'type': 'CALL' if option_type == 'C' else 'PUT',
                    'strike': strike,
                    'expiration': exp_date.strftime("%Y-%m-%d"),
                    'days_to_expiration': days_to_exp
                }
            else:
                # Fallback for non-standard symbols
                option_details = {
                    'underlying': symbol[:4],
                    'type': 'OPTION',
                    'strike': 0,
                    'expiration': 'Unknown',
                    'days_to_expiration': 0
                }
        
        # Calculate key metrics
        pct_of_portfolio = (cost_basis / float(client.get_account()['equity'])) * 100
        
        # Determine recommendation
        if is_option and option_details.get('days_to_expiration', 0) <= 1:
            recommendation = "CLOSE IMMEDIATELY - Expiring soon"
        elif unrealized_pct >= 50:
            recommendation = "CONSIDER PROFIT TAKING - 50%+ gain"
        elif unrealized_pct <= -30:
            recommendation = "REVIEW STOP LOSS - 30%+ loss"
        elif unrealized_pct > 0:
            recommendation = "HOLD - Profitable position"
        else:
            recommendation = "MONITOR - Underwater position"
        
        analysis.append({
            'symbol': symbol,
            'qty': int(qty),
            'entry_price': entry,
            'current_price': current,
            'cost_basis': cost_basis,
            'market_value': market_value,
            'unrealized_pl': unrealized,
            'unrealized_pct': unrealized_pct,
            'pct_of_portfolio': pct_of_portfolio,
            'is_option': is_option,
            'option_details': option_details,
            'recommendation': recommendation
        })
    
    return analysis

def main():
    print("=" * 100)
    print(f"📊 TRADENOVA DETAILED TRADE ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    # Initialize client
    client = AlpacaClient(paper=True)
    
    # Get account info
    account = client.get_account()
    equity = float(account['equity'])
    cash = float(account['cash'])
    buying_power = float(account['buying_power'])
    
    print(f"\n{'='*50}")
    print("📈 ACCOUNT SUMMARY")
    print(f"{'='*50}")
    print(f"   Total Equity:  ${equity:,.2f}")
    print(f"   Cash:          ${cash:,.2f}")
    print(f"   Buying Power:  ${buying_power:,.2f}")
    
    # Analyze positions
    print(f"\n{'='*100}")
    print("🔍 DETAILED POSITION ANALYSIS")
    print(f"{'='*100}")
    
    positions = analyze_positions(client)
    
    if not positions:
        print("\n   No open positions.")
    else:
        total_unrealized = 0
        total_cost = 0
        
        for i, pos in enumerate(positions, 1):
            total_unrealized += pos['unrealized_pl']
            total_cost += pos['cost_basis']
            
            print(f"\n{'─'*100}")
            print(f"📍 POSITION #{i}: {pos['symbol']}")
            print(f"{'─'*100}")
            
            if pos['is_option']:
                opt = pos['option_details']
                print(f"\n   📋 OPTION DETAILS:")
                print(f"      Underlying:    {opt['underlying']}")
                print(f"      Type:          {opt['type']}")
                print(f"      Strike:        ${opt['strike']:.2f}")
                print(f"      Expiration:    {opt['expiration']} ({opt['days_to_expiration']} days)")
            
            print(f"\n   💰 POSITION METRICS:")
            print(f"      Quantity:      {pos['qty']} contracts")
            print(f"      Entry Price:   ${pos['entry_price']:.4f}")
            print(f"      Current Price: ${pos['current_price']:.4f}")
            print(f"      Cost Basis:    ${pos['cost_basis']:,.2f}")
            print(f"      Market Value:  ${pos['market_value']:,.2f}")
            
            pnl_emoji = "🟢" if pos['unrealized_pct'] >= 0 else "🔴"
            print(f"\n   {pnl_emoji} P&L ANALYSIS:")
            print(f"      Unrealized:    ${pos['unrealized_pl']:,.2f} ({pos['unrealized_pct']:+.2f}%)")
            print(f"      % of Portfolio: {pos['pct_of_portfolio']:.1f}%")
            
            # Price movement
            price_change = pos['current_price'] - pos['entry_price']
            price_change_pct = (price_change / pos['entry_price']) * 100 if pos['entry_price'] > 0 else 0
            print(f"      Price Change:  ${price_change:.4f} ({price_change_pct:+.2f}%)")
            
            print(f"\n   💡 RECOMMENDATION: {pos['recommendation']}")
            
            # Risk analysis
            if pos['is_option']:
                opt = pos['option_details']
                print(f"\n   ⚠️  RISK FACTORS:")
                if opt['days_to_expiration'] <= 3:
                    print(f"      ❗ THETA DECAY: High time decay risk ({opt['days_to_expiration']} days to exp)")
                if abs(pos['unrealized_pct']) > 25:
                    print(f"      ❗ VOLATILITY: Position showing {abs(pos['unrealized_pct']):.1f}% move")
                if pos['pct_of_portfolio'] > 15:
                    print(f"      ❗ CONCENTRATION: {pos['pct_of_portfolio']:.1f}% of portfolio in single position")
        
        print(f"\n{'='*100}")
        print("📊 PORTFOLIO SUMMARY")
        print(f"{'='*100}")
        print(f"   Total Positions:     {len(positions)}")
        print(f"   Total Cost Basis:    ${total_cost:,.2f}")
        print(f"   Total Unrealized:    ${total_unrealized:,.2f}")
        print(f"   Portfolio P&L %:     {(total_unrealized/total_cost)*100 if total_cost > 0 else 0:+.2f}%")
    
    # Parse logs for signal analysis
    log_file = Path('logs/tradenova_daily.log')
    if log_file.exists():
        print(f"\n{'='*100}")
        print("📝 SIGNAL & EXECUTION ANALYSIS (from logs)")
        print(f"{'='*100}")
        
        signals, rejections, executions, errors = parse_log_file(str(log_file))
        
        # Get unique signals by symbol
        unique_signals = {}
        for sig in signals:
            key = sig['symbol']
            if key not in unique_signals or sig.get('type') == 'multi_agent_final':
                unique_signals[key] = sig
        
        print(f"\n   📊 Signals Generated: {len(unique_signals)}")
        for sym, sig in unique_signals.items():
            emoji = "📈" if sig['direction'] in ['LONG', 'BUY'] else "📉"
            print(f"      {emoji} {sym}: {sig['direction']} @ {sig['confidence']:.1f}% ({sig['agent']})")
        
        print(f"\n   ✅ Executions: {len([e for e in executions if e.get('type') == 'options_order'])}")
        for ex in executions:
            if ex.get('type') == 'options_order':
                print(f"      → {ex['side'].upper()} {ex['qty']} {ex['symbol']}")
        
        if errors:
            print(f"\n   ❌ Errors Encountered: {len(errors)}")
            unique_errors = set()
            for err in errors[-10:]:  # Last 10 errors
                # Extract just the error type
                if 'unsupported format string' in err['error']:
                    unique_errors.add("Format string error (bid/ask None)")
                elif 'asset_class' in err['error']:
                    unique_errors.add("Invalid asset_class parameter")
                elif 'unauthorized' in err['error'].lower():
                    unique_errors.add("API authorization error")
                else:
                    # Truncate long errors
                    error_msg = err['error'][:80] + "..." if len(err['error']) > 80 else err['error']
                    unique_errors.add(error_msg)
            
            for err in unique_errors:
                print(f"      ⚠️  {err}")
    
    # Get orders for today
    print(f"\n{'='*100}")
    print("📋 TODAY'S ORDER HISTORY")
    print(f"{'='*100}")
    
    orders = client.get_orders(status='all', limit=50)
    
    filled_orders = [o for o in orders if o.get('status') == 'filled']
    canceled_orders = [o for o in orders if o.get('status') == 'canceled']
    
    print(f"\n   Filled Orders: {len(filled_orders)}")
    print(f"   Canceled Orders: {len(canceled_orders)}")
    
    if filled_orders:
        print(f"\n   📜 FILLED ORDERS:")
        for order in filled_orders[:15]:  # Last 15
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A').upper()
            qty = order.get('filled_qty', order.get('qty', 0))
            price = float(order.get('filled_avg_price', 0))
            print(f"      ✅ {side} {qty} {symbol} @ ${price:.4f}")
    
    # Final recommendations
    print(f"\n{'='*100}")
    print("💡 TRADING RECOMMENDATIONS")
    print(f"{'='*100}")
    
    # Positions expiring soon
    expiring_soon = [p for p in positions if p['is_option'] and p['option_details'].get('days_to_expiration', 999) <= 3]
    if expiring_soon:
        print("\n   ⏰ EXPIRING SOON (action required):")
        for p in expiring_soon:
            print(f"      • {p['symbol']} - {p['option_details']['days_to_expiration']} days to expiration")
            print(f"        Current P&L: ${p['unrealized_pl']:.2f} ({p['unrealized_pct']:+.2f}%)")
    
    # Profitable positions for potential profit-taking
    profitable = [p for p in positions if p['unrealized_pct'] > 20]
    if profitable:
        print("\n   🎯 CONSIDER PROFIT TAKING (20%+ gain):")
        for p in profitable:
            print(f"      • {p['symbol']}: ${p['unrealized_pl']:.2f} ({p['unrealized_pct']:+.2f}%)")
    
    # Losing positions for review
    losing = [p for p in positions if p['unrealized_pct'] < -15]
    if losing:
        print("\n   ⚠️  REVIEW LOSING POSITIONS (>15% loss):")
        for p in losing:
            print(f"      • {p['symbol']}: ${p['unrealized_pl']:.2f} ({p['unrealized_pct']:+.2f}%)")
    
    print(f"\n{'='*100}")
    print("✅ ANALYSIS COMPLETE")
    print(f"{'='*100}")

if __name__ == "__main__":
    main()

