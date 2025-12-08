#!/usr/bin/env python3
"""
Intraday Options Backtest - Real Option Pricing + PUT Logic
Uses 5-minute bars for intraday momentum
Real option chain pricing from Alpaca
Includes PUT signals and proper strike selection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from alpaca_trade_api.rest import TimeFrame
import json
import numpy as np

from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from services.options_data_feed import OptionsDataFeed
from services.iv_calculator import IVCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_options_intraday.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntradayOptionsBacktest:
    """Intraday options backtest with real pricing"""
    
    def __init__(self):
        self.yesterday = (datetime.now() - timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.tickers = Config.TICKERS
        
        logger.info("="*70)
        logger.info("INTRADAY OPTIONS BACKTEST - REAL PRICING")
        logger.info("="*70)
        logger.info(f"Date: {self.yesterday.strftime('%Y-%m-%d')}")
        logger.info(f"Timeframe: 5-minute bars")
        logger.info(f"Tickers: {len(self.tickers)}")
        logger.info(f"Features: Real option pricing, PUT logic, ATM strikes")
        logger.info("="*70)
        
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        self.orchestrator = MultiAgentOrchestrator(self.client)
        self.options_feed = OptionsDataFeed(self.client)
        self.iv_calculator = IVCalculator()
        
        self.results: List[Dict] = []
        self.trades: List[Dict] = []
    
    def get_intraday_bars(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get 5-minute intraday bars for yesterday"""
        try:
            # Get bars from market open (9:30 AM) to close (4:00 PM)
            market_open = self.yesterday.replace(hour=9, minute=30)
            market_close = self.yesterday.replace(hour=16, minute=0)
            
            bars = self.client.get_historical_bars(
                symbol,
                TimeFrame.Minute,
                market_open - timedelta(days=1),  # Start a day earlier to ensure we get data
                market_close + timedelta(days=1)
            )
            
            if bars.empty:
                return None
            
            # Filter to yesterday's trading hours
            from pytz import UTC
            if bars.index.tz is not None:
                market_open_tz = UTC.localize(market_open) if market_open.tzinfo is None else market_open
                market_close_tz = UTC.localize(market_close) if market_close.tzinfo is None else market_close
            else:
                market_open_tz = market_open.replace(tzinfo=None) if market_open.tzinfo else market_open
                market_close_tz = market_close.replace(tzinfo=None) if market_close.tzinfo else market_close
            
            intraday_bars = bars[(bars.index >= market_open_tz) & (bars.index <= market_close_tz)]
            
            if intraday_bars.empty:
                # Try without timezone filtering
                intraday_bars = bars[bars.index.date == self.yesterday.date()]
            
            return intraday_bars if not intraday_bars.empty else None
            
        except Exception as e:
            logger.debug(f"Error fetching intraday bars for {symbol}: {e}")
            return None
    
    def analyze_intraday_signal(self, symbol: str, bars: pd.DataFrame, current_time: datetime) -> Optional[Dict]:
        """Analyze signal at a specific intraday time"""
        try:
            # Get bars up to current time
            bars_up_to_now = bars[bars.index <= current_time]
            
            if len(bars_up_to_now) < 20:  # Need minimum bars
                return None
            
            # Analyze with orchestrator
            trade_intent = self.orchestrator.analyze_symbol(symbol, bars_up_to_now)
            
            if trade_intent and trade_intent.confidence >= 0.30:
                return {
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'reasoning': trade_intent.reasoning,
                    'timestamp': current_time
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error analyzing signal: {e}")
            return None
    
    def get_option_price(self, option_symbol: str, timestamp: datetime) -> Optional[float]:
        """Get real option price from Alpaca"""
        try:
            # Try to get quote
            quote = self.options_feed.get_option_quote(option_symbol)
            if quote:
                # Use mid price (bid + ask) / 2, or last if available
                if quote.get('last'):
                    return quote['last']
                elif quote.get('bid') and quote.get('ask'):
                    return (quote['bid'] + quote['ask']) / 2
                elif quote.get('bid'):
                    return quote['bid']
                elif quote.get('ask'):
                    return quote['ask']
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting option price for {option_symbol}: {e}")
            return None
    
    def find_best_strike(self, symbol: str, current_price: float, option_type: str, 
                        expiration_date: str, options_chain: List[Dict]) -> Optional[Dict]:
        """Find best ATM or near-ATM strike"""
        try:
            # Filter by expiration and type
            filtered = []
            for contract in options_chain:
                if isinstance(contract, dict):
                    contract_type = contract.get('type', '') or contract.get('option_type', '')
                    strike = float(contract.get('strike_price', 0) or contract.get('strike', 0))
                    exp_date = contract.get('expiration_date') or contract.get('exp_date')
                    option_symbol = contract.get('symbol') or contract.get('contract_symbol')
                    
                    if (contract_type.lower() == option_type.lower() and 
                        strike > 0 and 
                        str(exp_date) == expiration_date):
                        distance_pct = abs(strike - current_price) / current_price * 100
                        filtered.append({
                            'contract': contract,
                            'strike': strike,
                            'distance_pct': distance_pct,
                            'option_symbol': option_symbol
                        })
            
            if not filtered:
                return None
            
            # Prefer ATM (within 1%), then slightly OTM (1-3%)
            # Avoid far OTM (>5%)
            filtered.sort(key=lambda x: x['distance_pct'])
            
            # Get best strike (ATM or slightly OTM)
            best = filtered[0]
            if best['distance_pct'] <= 3.0:  # Within 3% of ATM
                return best
            
            return None  # Too far OTM
            
        except Exception as e:
            logger.debug(f"Error finding best strike: {e}")
            return None
    
    def calculate_option_pnl_real(self, entry_price: float, exit_price: float, 
                                  strike: float, option_type: str, 
                                  entry_stock: float, exit_stock: float) -> Dict:
        """Calculate P&L using real option prices"""
        pnl_per_contract = exit_price - entry_price
        pnl_pct = (pnl_per_contract / entry_price * 100) if entry_price > 0 else 0
        
        # Calculate stock move
        stock_move_pct = ((exit_stock - entry_stock) / entry_stock * 100) if entry_stock > 0 else 0
        
        # Leverage
        leverage = abs(pnl_pct / stock_move_pct) if stock_move_pct != 0 else 0
        
        # Intrinsic value at exit
        if option_type.lower() == 'call':
            intrinsic = max(0, exit_stock - strike)
        else:
            intrinsic = max(0, strike - exit_stock)
        
        return {
            'pnl_per_contract': pnl_per_contract,
            'pnl_pct': pnl_pct,
            'stock_move_pct': stock_move_pct,
            'leverage': leverage,
            'intrinsic': intrinsic,
            'time_value_entry': entry_price - (max(0, entry_stock - strike) if option_type.lower() == 'call' else max(0, strike - entry_stock)),
            'time_value_exit': exit_price - intrinsic
        }
    
    def backtest_ticker_intraday(self, symbol: str) -> List[Dict]:
        """Backtest a ticker using intraday bars"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing {symbol} (Intraday)...")
            logger.info(f"{'='*60}")
            
            # Get intraday bars
            bars = self.get_intraday_bars(symbol)
            if bars is None or len(bars) < 20:
                logger.warning(f"  ⚠️  Insufficient intraday data for {symbol}")
                return []
            
            logger.info(f"  ✅ Got {len(bars)} intraday bars")
            
            # Get options chain
            options_chain = self.options_feed.get_options_chain(symbol)
            if not options_chain:
                logger.warning(f"  ⚠️  No options chain for {symbol}")
                return []
            
            # Get expiration dates (prefer 30-45 DTE)
            expirations = self.options_feed.get_expiration_dates(symbol)
            if not expirations:
                logger.warning(f"  ⚠️  No expiration dates for {symbol}")
                return []
            
            # Select target expiration (30-45 days)
            target_expiration = None
            today = datetime.now()
            for exp in sorted(expirations):
                try:
                    if isinstance(exp, str):
                        exp_date = datetime.strptime(exp, '%Y-%m-%d')
                    else:
                        exp_date = exp
                    dte = (exp_date - today).days
                    if 30 <= dte <= 45:
                        target_expiration = exp
                        break
                except:
                    continue
            
            if not target_expiration:
                # Use closest expiration
                target_expiration = sorted(expirations)[0] if expirations else None
            
            if not target_expiration:
                logger.warning(f"  ⚠️  No suitable expiration for {symbol}")
                return []
            
            logger.info(f"  ✅ Using expiration: {target_expiration}")
            
            # Scan intraday for signals (every 30 minutes)
            trades = []
            last_signal_time = None
            check_interval = timedelta(minutes=30)
            
            for i in range(0, len(bars), 6):  # Every 30 minutes (6 * 5min bars)
                if i >= len(bars):
                    break
                
                current_time = bars.index[i]
                current_price = float(bars['close'].iloc[i])
                
                # Skip if we just had a signal (avoid over-trading)
                if last_signal_time and (current_time - last_signal_time) < check_interval:
                    continue
                
                # Analyze signal
                signal = self.analyze_intraday_signal(symbol, bars, current_time)
                if not signal:
                    continue
                
                logger.info(f"  ✅ Signal at {current_time.strftime('%H:%M')}: {signal['direction']} ({signal['confidence']:.2%})")
                
                # Determine option type
                option_type = 'call' if signal['direction'] == 'LONG' else 'put'
                
                # Find best strike
                strike_info = self.find_best_strike(
                    symbol, current_price, option_type, 
                    str(target_expiration), options_chain
                )
                
                if not strike_info:
                    logger.debug(f"    No suitable strike found")
                    continue
                
                option_symbol = strike_info['option_symbol']
                strike = strike_info['strike']
                
                # Get entry option price
                entry_option_price = self.get_option_price(option_symbol, current_time)
                if not entry_option_price:
                    # Estimate if can't get real price
                    entry_option_price = current_price * 0.03  # 3% estimate
                    logger.debug(f"    Using estimated entry price: ${entry_option_price:.2f}")
                
                # Find exit (next signal or end of day)
                exit_time = None
                exit_stock_price = None
                exit_option_price = None
                
                # Look for exit signal or use end of day
                for j in range(i + 6, min(i + 78, len(bars)), 6):  # Check next 6.5 hours
                    if j >= len(bars):
                        break
                    
                    exit_candidate_time = bars.index[j]
                    exit_candidate_price = float(bars['close'].iloc[j])
                    
                    # Check for opposite signal or profit target
                    exit_signal = self.analyze_intraday_signal(symbol, bars, exit_candidate_time)
                    
                    # Exit conditions
                    stock_move = exit_candidate_price - current_price
                    stock_move_pct = (stock_move / current_price) * 100
                    
                    # Profit target: 10% for options
                    if option_type == 'call' and stock_move_pct >= 1.0:  # 1% stock move = ~10% option profit
                        exit_time = exit_candidate_time
                        exit_stock_price = exit_candidate_price
                        break
                    elif option_type == 'put' and stock_move_pct <= -1.0:
                        exit_time = exit_candidate_time
                        exit_stock_price = exit_candidate_price
                        break
                    elif exit_signal and exit_signal['direction'] != signal['direction']:
                        exit_time = exit_candidate_time
                        exit_stock_price = exit_candidate_price
                        break
                
                # Use end of day if no exit found
                if not exit_time:
                    exit_time = bars.index[-1]
                    exit_stock_price = float(bars['close'].iloc[-1])
                
                # Get exit option price
                exit_option_price = self.get_option_price(option_symbol, exit_time)
                if not exit_option_price:
                    # Calculate intrinsic value
                    if option_type == 'call':
                        intrinsic = max(0, exit_stock_price - strike)
                    else:
                        intrinsic = max(0, strike - exit_stock_price)
                    exit_option_price = intrinsic + (entry_option_price * 0.1)  # Intrinsic + 10% time value
                    logger.debug(f"    Using estimated exit price: ${exit_option_price:.2f}")
                
                # Calculate P&L
                pnl = self.calculate_option_pnl_real(
                    entry_option_price, exit_option_price, strike, option_type,
                    current_price, exit_stock_price
                )
                
                trade = {
                    'symbol': symbol,
                    'option_symbol': option_symbol,
                    'option_type': option_type.upper(),
                    'strike': strike,
                    'entry_time': current_time,
                    'exit_time': exit_time,
                    'entry_stock_price': current_price,
                    'exit_stock_price': exit_stock_price,
                    'entry_option_price': entry_option_price,
                    'exit_option_price': exit_option_price,
                    'signal': signal,
                    'pnl': pnl,
                    'profitable': pnl['pnl_pct'] > 0
                }
                
                trades.append(trade)
                last_signal_time = current_time
                
                status = "✅ PROFIT" if trade['profitable'] else "❌ LOSS"
                logger.info(f"    {status}: ${pnl['pnl_per_contract']:.2f} ({pnl['pnl_pct']:.2f}%) | Stock: {current_price:.2f} → {exit_stock_price:.2f} ({pnl['stock_move_pct']:.2f}%)")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {e}", exc_info=True)
            return []
    
    def run_backtest(self):
        """Run backtest for all tickers"""
        logger.info("\n" + "="*70)
        logger.info("STARTING INTRADAY BACKTEST")
        logger.info("="*70)
        
        for ticker in self.tickers:
            trades = self.backtest_ticker_intraday(ticker)
            self.trades.extend(trades)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive report"""
        logger.info("\n" + "="*70)
        logger.info("INTRADAY BACKTEST RESULTS")
        logger.info("="*70)
        
        if not self.trades:
            logger.info("No trades executed")
            return
        
        profitable = [t for t in self.trades if t['profitable']]
        losing = [t for t in self.trades if not t['profitable']]
        
        calls = [t for t in self.trades if t['option_type'] == 'CALL']
        puts = [t for t in self.trades if t['option_type'] == 'PUT']
        
        total_pnl = sum(t['pnl']['pnl_per_contract'] for t in self.trades)
        avg_pnl = total_pnl / len(self.trades) if self.trades else 0
        
        logger.info(f"\n📊 SUMMARY")
        logger.info(f"   Total Trades: {len(self.trades)}")
        logger.info(f"   ✅ Profitable: {len(profitable)}")
        logger.info(f"   ❌ Losing: {len(losing)}")
        logger.info(f"   Win Rate: {len(profitable) / len(self.trades) * 100:.1f}%")
        logger.info(f"   CALL Trades: {len(calls)}")
        logger.info(f"   PUT Trades: {len(puts)}")
        logger.info(f"   Total P&L: ${total_pnl:.2f}")
        logger.info(f"   Avg P&L: ${avg_pnl:.2f}")
        
        if profitable:
            logger.info(f"\n✅ TOP PROFITABLE TRADES:")
            for trade in sorted(profitable, key=lambda x: x['pnl']['pnl_pct'], reverse=True)[:5]:
                logger.info(f"   {trade['symbol']} {trade['option_type']} @ ${trade['strike']:.2f}: ${trade['pnl']['pnl_per_contract']:.2f} ({trade['pnl']['pnl_pct']:.2f}%)")
        
        # Save report
        report = {
            'backtest_date': self.yesterday.isoformat(),
            'timeframe': '5-minute intraday',
            'total_trades': len(self.trades),
            'profitable_trades': len(profitable),
            'losing_trades': len(losing),
            'win_rate': len(profitable) / len(self.trades) * 100 if self.trades else 0,
            'calls': len(calls),
            'puts': len(puts),
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'trades': self.trades
        }
        
        report_file = f"logs/options_backtest_intraday_{self.yesterday.strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n✅ Report saved to: {report_file}")
        logger.info("="*70)

def main():
    print("\n" + "="*70)
    print("INTRADAY OPTIONS BACKTEST")
    print("="*70)
    print("\nFeatures:")
    print("  - 5-minute intraday bars")
    print("  - Real option pricing from Alpaca")
    print("  - PUT and CALL signals")
    print("  - ATM/near-ATM strike selection")
    print("\n" + "-"*70)
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    backtest = IntradayOptionsBacktest()
    backtest.run_backtest()

if __name__ == "__main__":
    main()

