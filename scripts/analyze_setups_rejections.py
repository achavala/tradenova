#!/usr/bin/env python3
"""
Analyze Setups and Rejections
Detailed analysis of what setups were found and why they were accepted/rejected
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from alpaca_client import AlpacaClient
from services.massive_price_feed import MassivePriceFeed
from services.options_data_feed import OptionsDataFeed
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_setups_and_rejections():
    """Analyze what setups were found and why they were accepted/rejected"""
    
    print("="*80)
    print("SETUPS & REJECTIONS ANALYSIS - 0-30 DTE OPTIONS")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize components
    massive_feed = MassivePriceFeed()
    alpaca_client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    orchestrator = MultiAgentOrchestrator(alpaca_client)
    trader = IntegratedTrader(dry_run=True, paper_trading=True)
    options_feed = OptionsDataFeed(alpaca_client)
    
    print("CONFIGURATION:")
    print("-" * 80)
    print(f"MIN_DTE: {Config.MIN_DTE} days")
    print(f"MAX_DTE: {Config.MAX_DTE} days")
    print(f"TARGET_DTE: {Config.TARGET_DTE} days")
    print()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    today = datetime.now().date()
    
    results = []
    
    print("ANALYZING EACH TICKER:")
    print("="*80)
    
    for symbol in Config.TICKERS:
        print(f"\n{symbol}:")
        print("-" * 80)
        
        result = {
            'symbol': symbol,
            'signal_generated': False,
            'signal_direction': None,
            'signal_confidence': None,
            'signal_agent': None,
            'rejected_reasons': [],
            'options_available': False,
            'expiration_found': False,
            'atm_option_found': False,
            'execution_attempted': False,
            'execution_successful': False
        }
        
        try:
            # Get data
            bars = None
            if massive_feed.is_available():
                bars = massive_feed.get_daily_bars(symbol, start_date, end_date, use_1min_aggregation=True)
            else:
                from alpaca_trade_api.rest import TimeFrame
                bars = alpaca_client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
            
            if bars.empty or len(bars) < 30:
                result['rejected_reasons'].append(f"Insufficient data: {len(bars)} bars (need 30+)")
                print(f"  ❌ Insufficient data: {len(bars)} bars")
                results.append(result)
                continue
            
            # Set timestamp as index if needed
            if 'timestamp' in bars.columns:
                bars = bars.set_index('timestamp')
            
            current_price = bars['close'].iloc[-1]
            print(f"  ✅ Data: {len(bars)} bars, Price: ${current_price:.2f}")
            
            # Generate signal
            intent = orchestrator.analyze_symbol(symbol, bars)
            
            if not intent or intent.direction.value == 'FLAT':
                result['rejected_reasons'].append("No signal generated (FLAT)")
                print(f"  ❌ No signal generated")
                results.append(result)
                continue
            
            result['signal_generated'] = True
            result['signal_direction'] = intent.direction.value
            result['signal_confidence'] = intent.confidence
            result['signal_agent'] = intent.agent_name
            
            print(f"  ✅ Signal: {intent.direction.value} @ {intent.confidence:.2%} ({intent.agent_name})")
            
            # Check if LONG (we only buy LONG options)
            if intent.direction.value != 'LONG':
                result['rejected_reasons'].append(f"Signal is {intent.direction.value} (only buying LONG options)")
                print(f"  ⚠️  Rejected: Only buying LONG options (signal was {intent.direction.value})")
                results.append(result)
                continue
            
            # Check options availability
            expirations = options_feed.get_expiration_dates(symbol)
            if not expirations:
                result['rejected_reasons'].append("No expiration dates found")
                print(f"  ❌ No expiration dates found")
                results.append(result)
                continue
            
            result['options_available'] = True
            print(f"  ✅ Options available: {len(expirations)} expirations")
            
            # Check for 0-30 DTE expiration
            target_expiration = None
            for exp_date in sorted(expirations):
                if isinstance(exp_date, str):
                    exp_date = datetime.strptime(exp_date, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                if Config.MIN_DTE <= dte <= Config.MAX_DTE:
                    target_expiration = exp_date
                    break
            
            if not target_expiration:
                result['rejected_reasons'].append(f"No expiration in {Config.MIN_DTE}-{Config.MAX_DTE} DTE range")
                print(f"  ❌ No expiration in {Config.MIN_DTE}-{Config.MAX_DTE} DTE range")
                print(f"     Available expirations: {expirations[:5]}")
                results.append(result)
                continue
            
            result['expiration_found'] = True
            dte = (target_expiration - today).days
            print(f"  ✅ Expiration found: {target_expiration} (DTE: {dte})")
            
            # Check for ATM option
            option_contract = options_feed.get_atm_options(
                symbol,
                target_expiration.strftime('%Y-%m-%d'),
                'call'
            )
            
            if not option_contract:
                result['rejected_reasons'].append(f"No ATM call option found for expiration {target_expiration}")
                print(f"  ❌ No ATM call option found")
                results.append(result)
                continue
            
            result['atm_option_found'] = True
            option_symbol = option_contract.get('symbol') or option_contract.get('contract_symbol')
            strike = option_contract.get('strike_price', 'N/A')
            print(f"  ✅ ATM option found: {option_symbol} (strike: ${strike})")
            
            # Check quote
            quote = options_feed.get_option_quote(option_symbol)
            if not quote:
                result['rejected_reasons'].append(f"No quote available for option {option_symbol}")
                print(f"  ❌ No quote available")
                results.append(result)
                continue
            
            # Get price
            option_price = quote.get('last_price') or quote.get('mid_price')
            if not option_price:
                bid = quote.get('bid', 0)
                ask = quote.get('ask', 0)
                if bid > 0 and ask > 0:
                    option_price = (bid + ask) / 2
                else:
                    result['rejected_reasons'].append(f"No valid price for option (bid: ${bid}, ask: ${ask})")
                    print(f"  ❌ No valid price")
                    results.append(result)
                    continue
            
            print(f"  ✅ Option price: ${option_price:.2f}")
            
            # Check position size
            account = alpaca_client.get_account()
            balance = float(account['equity'])
            position_capital = balance * Config.POSITION_SIZE_PCT / Config.MAX_ACTIVE_TRADES
            contracts = int(position_capital / (option_price * 100))
            
            if contracts < 1:
                result['rejected_reasons'].append(f"Position size too small: ${position_capital:.2f} < ${option_price * 100:.2f} (1 contract)")
                print(f"  ❌ Position size too small: ${position_capital:.2f} < ${option_price * 100:.2f}")
                results.append(result)
                continue
            
            print(f"  ✅ Position size: {contracts} contracts (${position_capital:.2f} capital)")
            
            # Check risk
            iv_rank = None
            try:
                from services.iv_rank_service import IVRankService
                iv_service = IVRankService()
                metrics = iv_service.get_iv_metrics(symbol)
                iv_rank = metrics.get('iv_rank')
            except:
                pass
            
            positions = alpaca_client.get_positions()
            current_positions = []
            for pos in positions:
                current_positions.append({
                    'symbol': pos['symbol'],
                    'qty': float(pos['qty']),
                    'entry_price': pos.get('avg_entry_price', 0),
                    'current_price': pos.get('current_price', 0)
                })
            
            allowed, reason, risk_level = trader.risk_manager.check_trade_allowed(
                symbol=symbol,
                qty=contracts,
                price=current_price,
                side='buy',
                iv_rank=iv_rank,
                current_positions=current_positions
            )
            
            if not allowed:
                result['rejected_reasons'].append(f"Risk check failed: {reason} (risk_level: {risk_level})")
                print(f"  ❌ Risk check failed: {reason}")
                results.append(result)
                continue
            
            print(f"  ✅ Risk check passed: {risk_level}")
            
            # All checks passed
            result['execution_attempted'] = True
            result['execution_successful'] = True
            print(f"  ✅ ALL CHECKS PASSED - Would execute options trade")
            
            results.append(result)
            
        except Exception as e:
            result['rejected_reasons'].append(f"Error: {str(e)}")
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append(result)
    
    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    signals_found = sum(1 for r in results if r.get('signal_generated'))
    long_signals = sum(1 for r in results if r.get('signal_direction') == 'LONG')
    options_available = sum(1 for r in results if r.get('options_available'))
    expiration_found = sum(1 for r in results if r.get('expiration_found'))
    atm_found = sum(1 for r in results if r.get('atm_option_found'))
    execution_ready = sum(1 for r in results if r.get('execution_successful'))
    
    print(f"Total Tickers: {len(results)}")
    print(f"Signals Generated: {signals_found}")
    print(f"LONG Signals: {long_signals}")
    print(f"Options Available: {options_available}")
    print(f"Expiration in 0-30 DTE: {expiration_found}")
    print(f"ATM Option Found: {atm_found}")
    print(f"Ready to Execute: {execution_ready}")
    print()
    
    # Detailed breakdown
    print("DETAILED BREAKDOWN:")
    print("-" * 80)
    
    for r in results:
        symbol = r['symbol']
        print(f"\n{symbol}:")
        
        if not r.get('signal_generated'):
            print(f"  ❌ No signal")
            if r.get('rejected_reasons'):
                for reason in r['rejected_reasons']:
                    print(f"     - {reason}")
            continue
        
        print(f"  ✅ Signal: {r['signal_direction']} @ {r['signal_confidence']:.2%} ({r['signal_agent']})")
        
        if r['signal_direction'] != 'LONG':
            print(f"  ⚠️  Rejected: Only buying LONG options")
            continue
        
        if not r.get('options_available'):
            print(f"  ❌ No options available")
            if r.get('rejected_reasons'):
                for reason in r['rejected_reasons']:
                    print(f"     - {reason}")
            continue
        
        if not r.get('expiration_found'):
            print(f"  ❌ No expiration in 0-30 DTE range")
            if r.get('rejected_reasons'):
                for reason in r['rejected_reasons']:
                    print(f"     - {reason}")
            continue
        
        if not r.get('atm_option_found'):
            print(f"  ❌ No ATM option found")
            if r.get('rejected_reasons'):
                for reason in r['rejected_reasons']:
                    print(f"     - {reason}")
            continue
        
        if r.get('execution_successful'):
            print(f"  ✅ READY TO EXECUTE")
        else:
            print(f"  ⚠️  Rejected:")
            for reason in r.get('rejected_reasons', []):
                print(f"     - {reason}")
    
    print()
    print("="*80)
    print("CONCLUSION")
    print("="*80)
    
    if execution_ready > 0:
        print(f"✅ {execution_ready} setup(s) ready to execute options trades")
    else:
        print("⚠️  No setups ready to execute")
        print("\nRejection reasons:")
        all_reasons = {}
        for r in results:
            for reason in r.get('rejected_reasons', []):
                all_reasons[reason] = all_reasons.get(reason, 0) + 1
        
        for reason, count in sorted(all_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {reason}: {count} ticker(s)")
    
    return results

if __name__ == "__main__":
    results = analyze_setups_and_rejections()
    sys.exit(0)

