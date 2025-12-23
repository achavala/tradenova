#!/usr/bin/env python3
"""
Comprehensive Investigation: Why No Trades Today
Detailed analysis of all system components
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from alpaca_client import AlpacaClient
from config import Config
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_market_status():
    """Check if market is open"""
    print("="*80)
    print("1. MARKET STATUS CHECK")
    print("="*80)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        is_open = client.is_market_open()
        clock = client.api.get_clock()
        
        print(f"Market Open: {is_open}")
        print(f"Current Time: {clock.timestamp}")
        print(f"Next Open: {clock.next_open}")
        print(f"Next Close: {clock.next_close}")
        print()
        
        return is_open, client
    except Exception as e:
        print(f"❌ Error checking market status: {e}")
        return None, None

def check_account_status(client):
    """Check account status"""
    print("="*80)
    print("2. ACCOUNT STATUS")
    print("="*80)
    
    try:
        account = client.get_account()
        print(f"Equity: ${float(account['equity']):,.2f}")
        print(f"Buying Power: ${float(account['buying_power']):,.2f}")
        print(f"Cash: ${float(account['cash']):,.2f}")
        print(f"Account Blocked: {account.get('account_blocked', False)}")
        print(f"Trading Blocked: {account.get('trading_blocked', False)}")
        print(f"Pattern Day Trader: {account.get('pattern_day_trader', False)}")
        print()
        
        positions = client.get_positions()
        print(f"Current Positions: {len(positions)}")
        if positions:
            for pos in positions[:5]:
                print(f"  - {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
        print()
        
        return account, positions
    except Exception as e:
        print(f"❌ Error checking account: {e}")
        return None, []

def check_data_availability(client):
    """Check data availability for tickers"""
    print("="*80)
    print("3. DATA AVAILABILITY CHECK")
    print("="*80)
    
    today = datetime.now()
    start_date = today - timedelta(days=60)
    
    results = {}
    
    for symbol in Config.TICKERS[:3]:  # Check first 3 for speed
        try:
            # Check Alpaca data
            bars = client.get_historical_bars(
                symbol, 
                'Day', 
                start_date, 
                today
            )
            
            # Check current price
            current_price = client.get_latest_price(symbol)
            
            results[symbol] = {
                'bars_count': len(bars) if not bars.empty else 0,
                'current_price': current_price,
                'has_data': len(bars) >= 30 if not bars.empty else False
            }
            
            print(f"{symbol}:")
            print(f"  Bars: {results[symbol]['bars_count']} (need 30+)")
            print(f"  Current Price: ${current_price:.2f}" if current_price else "  Current Price: N/A")
            print(f"  Has Enough Data: {results[symbol]['has_data']}")
            print()
            
        except Exception as e:
            print(f"{symbol}: ❌ Error - {e}")
            results[symbol] = {'error': str(e)}
            print()
    
    return results

def check_options_availability(client):
    """Check options chain availability"""
    print("="*80)
    print("4. OPTIONS CHAIN AVAILABILITY")
    print("="*80)
    
    try:
        from services.options_data_feed import OptionsDataFeed
        
        options_feed = OptionsDataFeed(client)
        
        # Check first ticker
        symbol = Config.TICKERS[0]
        print(f"Checking options for {symbol}...")
        
        # Get expiration dates
        expirations = options_feed.get_expiration_dates(symbol)
        print(f"Available Expirations: {len(expirations)}")
        
        if expirations:
            today = datetime.now().date()
            valid_expirations = []
            for exp in expirations[:5]:
                try:
                    if isinstance(exp, str):
                        exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                    else:
                        exp_date = exp
                    
                    dte = (exp_date - today).days
                    if 0 <= dte <= 30:
                        valid_expirations.append((exp, dte))
                        print(f"  ✅ {exp} (DTE: {dte})")
                    else:
                        print(f"  ⚠️  {exp} (DTE: {dte} - outside 0-30 range)")
                except Exception as e:
                    print(f"  ❌ {exp} - Error parsing: {e}")
            
            print(f"\nValid 0-30 DTE Expirations: {len(valid_expirations)}")
            
            # Try to get ATM option for first valid expiration
            if valid_expirations:
                target_exp = valid_expirations[0][0]
                print(f"\nTesting ATM option retrieval for {target_exp}...")
                
                try:
                    atm_call = options_feed.get_atm_options(symbol, target_exp, 'call')
                    atm_put = options_feed.get_atm_options(symbol, target_exp, 'put')
                    
                    if atm_call:
                        print(f"  ✅ CALL option found")
                        print(f"     Symbol: {atm_call.get('symbol', 'N/A')}")
                        print(f"     Strike: ${atm_call.get('strike_price', 'N/A')}")
                    else:
                        print(f"  ❌ No CALL option found")
                    
                    if atm_put:
                        print(f"  ✅ PUT option found")
                        print(f"     Symbol: {atm_put.get('symbol', 'N/A')}")
                        print(f"     Strike: ${atm_put.get('strike_price', 'N/A')}")
                    else:
                        print(f"  ❌ No PUT option found")
                        
                except Exception as e:
                    print(f"  ❌ Error getting ATM options: {e}")
        else:
            print("❌ No expiration dates found")
        
        print()
        return len(expirations) > 0
        
    except Exception as e:
        print(f"❌ Error checking options: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_logs_for_signals():
    """Check logs for signals and rejections"""
    print("="*80)
    print("5. LOG ANALYSIS - SIGNALS & REJECTIONS")
    print("="*80)
    
    log_file = Path("logs/tradenova_daily.log")
    if not log_file.exists():
        print("❌ Log file not found")
        return
    
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    
    signals = []
    rejections = []
    executions = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if today_str in line:
                if "Signal for" in line or "best_signal" in line.lower():
                    signals.append(line.strip())
                if "BLOCKED" in line or "rejected" in line.lower() or "skipping" in line.lower():
                    rejections.append(line.strip())
                if "EXECUTING" in line or "TRADE EXECUTED" in line or "OPTIONS TRADE" in line:
                    executions.append(line.strip())
    
    print(f"Signals Found Today: {len(signals)}")
    for sig in signals[-10:]:  # Last 10
        print(f"  {sig}")
    print()
    
    print(f"Rejections/Blocks Found Today: {len(rejections)}")
    for rej in rejections[-10:]:  # Last 10
        print(f"  {rej}")
    print()
    
    print(f"Executions Found Today: {len(executions)}")
    for exe in executions[-10:]:  # Last 10
        print(f"  {exe}")
    print()

def check_system_running():
    """Check if system is running"""
    print("="*80)
    print("6. SYSTEM STATUS")
    print("="*80)
    
    import subprocess
    
    # Check for running processes
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        processes = result.stdout
        run_daily_running = 'run_daily.py' in processes
        integrated_trader_running = 'integrated_trader' in processes
        
        print(f"run_daily.py Running: {run_daily_running}")
        print(f"IntegratedTrader Running: {integrated_trader_running}")
        print()
        
        if run_daily_running:
            print("✅ Trading system appears to be running")
        else:
            print("❌ Trading system does NOT appear to be running")
            print("   Start with: python3 run_daily.py --paper")
        print()
        
    except Exception as e:
        print(f"Error checking processes: {e}")
        print()

def check_configuration():
    """Check configuration"""
    print("="*80)
    print("7. CONFIGURATION CHECK")
    print("="*80)
    
    print(f"Tickers: {Config.TICKERS}")
    print(f"Max Active Trades: {Config.MAX_ACTIVE_TRADES}")
    print(f"Position Size %: {Config.POSITION_SIZE_PCT*100}%")
    print(f"Min DTE: {Config.MIN_DTE}")
    print(f"Max DTE: {Config.MAX_DTE}")
    print(f"Alpaca Base URL: {Config.ALPACA_BASE_URL}")
    print(f"Massive API Key: {'✅ Set' if Config.MASSIVE_API_KEY else '❌ Not Set'}")
    print()

def main():
    """Main investigation"""
    print("\n" + "="*80)
    print("COMPREHENSIVE INVESTIGATION: WHY NO TRADES TODAY")
    print("="*80)
    print(f"Investigation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Market Status
    is_open, client = check_market_status()
    
    if not client:
        print("❌ Cannot proceed - Alpaca client failed")
        return
    
    # 2. Account Status
    account, positions = check_account_status(client)
    
    # 3. Data Availability
    data_results = check_data_availability(client)
    
    # 4. Options Availability
    options_available = check_options_availability(client)
    
    # 5. Log Analysis
    check_logs_for_signals()
    
    # 6. System Status
    check_system_running()
    
    # 7. Configuration
    check_configuration()
    
    # Summary
    print("="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)
    
    issues = []
    
    if not is_open:
        issues.append("❌ Market is CLOSED")
    
    if account and account.get('trading_blocked'):
        issues.append("❌ Trading is BLOCKED on account")
    
    if account and float(account.get('buying_power', 0)) < 100:
        issues.append("❌ Insufficient buying power")
    
    if not options_available:
        issues.append("❌ Options chain not available")
    
    if len(positions) >= Config.MAX_ACTIVE_TRADES:
        issues.append(f"⚠️  Max positions reached ({len(positions)}/{Config.MAX_ACTIVE_TRADES})")
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ No obvious issues found")
        print("   Check logs for signal generation and rejection reasons")
    
    print()
    print("Next Steps:")
    print("  1. Review detailed logs: tail -f logs/tradenova_daily.log")
    print("  2. Check for signals: grep 'Signal for' logs/tradenova_daily.log")
    print("  3. Check for rejections: grep 'BLOCKED\\|rejected' logs/tradenova_daily.log")
    print("  4. Verify system is running: ps aux | grep run_daily")
    print()

if __name__ == '__main__':
    main()

