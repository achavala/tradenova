#!/usr/bin/env python3
"""
Backtest TradeNova Options Trading System
December 12-19, 2025 (1 Week)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.agents.base_agent import TradeDirection
from services.options_data_feed import OptionsDataFeed
from services.polygon_options_feed import MassiveOptionsFeed
from services.massive_price_feed import MassivePriceFeed
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptionsBacktester:
    """Backtest options trading system"""
    
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
        self.trades: List[Dict] = []
        self.signals: List[Dict] = []
        self.rejected: List[Dict] = []
        
        # Initialize clients
        self.alpaca_client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        # Initialize Massive feeds
        self.massive_price_feed = MassivePriceFeed()
        self.massive_options_feed = MassiveOptionsFeed()
        self.options_feed = OptionsDataFeed(self.alpaca_client)
        self.orchestrator = MultiAgentOrchestrator(self.alpaca_client)
        
    def get_historical_bars(self, symbol: str, date: datetime) -> Optional[pd.DataFrame]:
        """Get historical bars for a specific date"""
        try:
            # Get 60 days of history ending on the date
            end = date
            start = end - timedelta(days=60)
            
            # Try Massive first
            if self.massive_price_feed.is_available():
                bars = self.massive_price_feed.get_daily_bars(symbol, start, end)
                if not bars.empty and len(bars) >= 30:
                    return bars
            
            # Fallback to Alpaca (limited history)
            from alpaca_trade_api.rest import TimeFrame
            bars = self.alpaca_client.get_historical_bars(symbol, TimeFrame.Day, start, end)
            if not bars.empty and len(bars) >= 30:
                return bars
            
            return None
        except Exception as e:
            logger.debug(f"Error getting bars for {symbol} on {date}: {e}")
            return None
    
    def get_options_chain_historical(self, symbol: str, date: datetime) -> List[Dict]:
        """Get options chain for a specific date"""
        try:
            # Use Massive for historical options data
            if self.massive_options_feed.is_available():
                date_str = date.strftime('%Y-%m-%d')
                chain = self.massive_options_feed.get_options_chain(
                    symbol,
                    date=date_str,
                    as_of_date=date_str
                )
                if chain:
                    return chain
            
            # Fallback: Try to get current chain (approximation)
            chain = self.options_feed.get_options_chain(symbol)
            return chain
        except Exception as e:
            logger.debug(f"Error getting options chain for {symbol} on {date}: {e}")
            return []
    
    def get_stock_price_historical(self, symbol: str, date: datetime) -> Optional[float]:
        """Get stock price for a specific date"""
        try:
            bars = self.get_historical_bars(symbol, date)
            if bars is not None and not bars.empty:
                # Get the last bar (closest to the date)
                return float(bars.iloc[-1]['close'])
            return None
        except Exception as e:
            logger.debug(f"Error getting price for {symbol} on {date}: {e}")
            return None
    
    def find_atm_option(self, symbol: str, current_price: float, expiration_date: str, option_type: str, date: datetime) -> Optional[Dict]:
        """Find ATM option for historical date"""
        try:
            chain = self.get_options_chain_historical(symbol, date)
            if not chain:
                return None
            
            # Filter by type
            filtered = []
            for contract in chain:
                contract_type = contract.get('type', '').lower()
                if isinstance(contract, dict):
                    details = contract.get('details', {})
                    if details:
                        contract_type = details.get('contract_type', '').lower()
                
                if contract_type == option_type.lower():
                    filtered.append(contract)
            
            if not filtered:
                return None
            
            # Find closest to ATM
            atm_option = min(
                filtered,
                key=lambda x: abs(float(x.get('strike_price', 0) or x.get('details', {}).get('strike_price', 0)) - current_price)
            )
            
            return atm_option
        except Exception as e:
            logger.debug(f"Error finding ATM option for {symbol}: {e}")
            return None
    
    def get_option_price_historical(self, option_contract: Dict, symbol: str, date: datetime) -> Optional[float]:
        """Get option price for historical date"""
        try:
            # Try to get from contract data
            close_price = option_contract.get('close_price')
            if close_price:
                return float(close_price)
            
            # Try Massive historical data
            if self.massive_options_feed.is_available():
                date_str = date.strftime('%Y-%m-%d')
                strike = float(option_contract.get('strike_price', 0) or option_contract.get('details', {}).get('strike_price', 0))
                option_type = option_contract.get('type', '').lower() or option_contract.get('details', {}).get('contract_type', '').lower()
                
                chain = self.massive_options_feed.get_options_chain(
                    symbol,
                    date=date_str,
                    as_of_date=date_str
                )
                
                for contract in chain:
                    details = contract.get('details', {})
                    contract_strike = float(details.get('strike_price', 0))
                    contract_type = details.get('contract_type', '').lower()
                    
                    if abs(contract_strike - strike) < 0.01 and contract_type == option_type:
                        day_data = contract.get('day', {})
                        price = day_data.get('close') or day_data.get('open')
                        if price:
                            return float(price)
            
            return None
        except Exception as e:
            logger.debug(f"Error getting option price: {e}")
            return None
    
    def backtest_day(self, date: datetime):
        """Backtest a single day"""
        print(f"\n{'='*60}")
        print(f"BACKTESTING: {date.strftime('%Y-%m-%d %A')}")
        print(f"{'='*60}")
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTESTING: {date.strftime('%Y-%m-%d %A')}")
        logger.info(f"{'='*60}")
        
        day_trades = []
        day_signals = []
        day_rejected = []
        
        for idx, symbol in enumerate(Config.TICKERS, 1):
            try:
                print(f"  [{idx}/{len(Config.TICKERS)}] Processing {symbol}...", end='\r')
                # Get historical bars
                bars = self.get_historical_bars(symbol, date)
                if bars is None or bars.empty or len(bars) < 30:
                    logger.debug(f"  {symbol}: Insufficient data ({len(bars) if bars is not None else 0} bars)")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': f'Insufficient data ({len(bars) if bars is not None else 0} bars)'
                    })
                    continue
                
                # Get current price
                current_price = self.get_stock_price_historical(symbol, date)
                if current_price is None:
                    logger.debug(f"  {symbol}: No price available")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': 'No price available'
                    })
                    continue
                
                # Generate signal
                intent = self.orchestrator.analyze_symbol(symbol, bars)
                if not intent or intent.direction == TradeDirection.FLAT:
                    logger.debug(f"  {symbol}: No signal (FLAT)")
                    continue
                
                if intent.confidence < 0.6:
                    logger.debug(f"  {symbol}: Signal confidence too low ({intent.confidence:.2%})")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': f'Confidence too low ({intent.confidence:.2%})',
                        'direction': intent.direction.value,
                        'confidence': intent.confidence
                    })
                    continue
                
                # Record signal
                signal_info = {
                    'symbol': symbol,
                    'date': date,
                    'direction': intent.direction.value,
                    'confidence': intent.confidence,
                    'agent': intent.agent_name,
                    'current_price': current_price
                }
                day_signals.append(signal_info)
                print(f"  ✅ {symbol}: {intent.direction.value} @ {intent.confidence:.2%} ({intent.agent_name})")
                logger.info(f"  ✅ {symbol}: {intent.direction.value} @ {intent.confidence:.2%} ({intent.agent_name})")
                
                # Determine option type
                option_type = 'call' if intent.direction.value == 'LONG' else 'put'
                
                # Get options expirations (use current expirations as approximation)
                # Note: For historical backtest, we use current expirations as proxy
                expirations = self.options_feed.get_expiration_dates(symbol)
                if not expirations:
                    logger.debug(f"  {symbol}: No expirations available")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': 'No expirations available',
                        'direction': intent.direction.value
                    })
                    continue
                
                # Find expiration in 0-30 DTE range
                today = date.date()
                target_expiration = None
                for exp_date in sorted(expirations):
                    if isinstance(exp_date, str):
                        exp_date = datetime.strptime(exp_date, '%Y-%m-%d').date()
                    dte = (exp_date - today).days
                    if Config.MIN_DTE <= dte <= Config.MAX_DTE:
                        target_expiration = exp_date
                        break
                
                if not target_expiration:
                    logger.debug(f"  {symbol}: No expiration in 0-30 DTE range")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': 'No expiration in 0-30 DTE range',
                        'direction': intent.direction.value
                    })
                    continue
                
                # Find ATM option
                atm_option = self.find_atm_option(
                    symbol, current_price, 
                    target_expiration.strftime('%Y-%m-%d'),
                    option_type, date
                )
                
                if not atm_option:
                    logger.debug(f"  {symbol}: No ATM {option_type} option found")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': f'No ATM {option_type} option found',
                        'direction': intent.direction.value
                    })
                    continue
                
                # Get option symbol
                option_symbol = (
                    atm_option.get('symbol') or 
                    atm_option.get('contract_symbol') or
                    atm_option.get('ticker') or
                    atm_option.get('name')
                )
                
                if not option_symbol:
                    logger.debug(f"  {symbol}: No option symbol found")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': 'No option symbol found',
                        'direction': intent.direction.value
                    })
                    continue
                
                # Get option price
                option_price = self.get_option_price_historical(atm_option, symbol, date)
                if not option_price or option_price <= 0:
                    logger.debug(f"  {symbol}: No option price available")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': 'No option price available',
                        'direction': intent.direction.value,
                        'option_symbol': option_symbol
                    })
                    continue
                
                # Calculate position size (simplified - assume $100k account)
                account_balance = 100000
                options_position_pct = min(Config.POSITION_SIZE_PCT * 1.5, 0.75)
                position_capital = account_balance * options_position_pct / Config.MAX_ACTIVE_TRADES
                contract_cost = option_price * 100
                contracts = int(position_capital / contract_cost)
                
                if contracts < 1:
                    logger.debug(f"  {symbol}: Position too small (${position_capital:.2f} < ${contract_cost:.2f})")
                    day_rejected.append({
                        'symbol': symbol,
                        'date': date,
                        'reason': f'Position too small (${position_capital:.2f} < ${contract_cost:.2f})',
                        'direction': intent.direction.value,
                        'option_symbol': option_symbol,
                        'option_price': option_price
                    })
                    continue
                
                # Record trade
                strike = float(atm_option.get('strike_price', 0) or atm_option.get('details', {}).get('strike_price', 0))
                trade = {
                    'symbol': symbol,
                    'date': date,
                    'option_symbol': option_symbol,
                    'option_type': option_type.upper(),
                    'direction': intent.direction.value,
                    'strike': strike,
                    'expiration': target_expiration,
                    'dte': (target_expiration - today).days,
                    'option_price': option_price,
                    'contracts': contracts,
                    'total_cost': contracts * contract_cost,
                    'confidence': intent.confidence,
                    'agent': intent.agent_name,
                    'current_stock_price': current_price
                }
                day_trades.append(trade)
                
                print(f"    📊 TRADE: {option_symbol} ({option_type.upper()})")
                print(f"       Strike: ${strike:.2f}, Price: ${option_price:.2f}")
                print(f"       Contracts: {contracts}, Total: ${contracts * contract_cost:,.2f}")
                logger.info(f"    📊 TRADE: {option_symbol} ({option_type.upper()})")
                logger.info(f"       Strike: ${strike:.2f}, Price: ${option_price:.2f}")
                logger.info(f"       Contracts: {contracts}, Total: ${contracts * contract_cost:,.2f}")
                logger.info(f"       Expiration: {target_expiration} (DTE: {(target_expiration - today).days})")
                
            except Exception as e:
                logger.error(f"Error backtesting {symbol} on {date}: {e}", exc_info=True)
                day_rejected.append({
                    'symbol': symbol,
                    'date': date,
                    'reason': f'Error: {str(e)}'
                })
        
        self.trades.extend(day_trades)
        self.signals.extend(day_signals)
        self.rejected.extend(day_rejected)
        
        return day_trades, day_signals, day_rejected
    
    def run_backtest(self):
        """Run full backtest"""
        logger.info(f"\n{'='*60}")
        logger.info(f"OPTIONS TRADING BACKTEST")
        logger.info(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Tickers: {', '.join(Config.TICKERS)}")
        logger.info(f"Options: 0-30 DTE, LONG→CALL, SHORT→PUT")
        logger.info(f"{'='*60}\n")
        
        # Backtest each trading day
        current_date = self.start_date
        while current_date <= self.end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                self.backtest_day(current_date)
            current_date += timedelta(days=1)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate detailed backtest report"""
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTEST RESULTS SUMMARY")
        logger.info(f"{'='*60}\n")
        
        # Statistics
        total_signals = len(self.signals)
        total_trades = len(self.trades)
        total_rejected = len(self.rejected)
        
        long_signals = len([s for s in self.signals if s['direction'] == 'LONG'])
        short_signals = len([s for s in self.signals if s['direction'] == 'SHORT'])
        
        call_trades = len([t for t in self.trades if t['option_type'] == 'CALL'])
        put_trades = len([t for t in self.trades if t['option_type'] == 'PUT'])
        
        total_cost = sum(t['total_cost'] for t in self.trades)
        
        logger.info(f"📊 STATISTICS:")
        logger.info(f"   Total Signals Generated: {total_signals}")
        logger.info(f"     - LONG: {long_signals}")
        logger.info(f"     - SHORT: {short_signals}")
        logger.info(f"   Total Trades Executed: {total_trades}")
        logger.info(f"     - CALL: {call_trades}")
        logger.info(f"     - PUT: {put_trades}")
        logger.info(f"   Total Rejected: {total_rejected}")
        logger.info(f"   Total Capital Required: ${total_cost:,.2f}")
        logger.info(f"")
        
        # Trades by day
        logger.info(f"📅 TRADES BY DAY:")
        trades_by_day = {}
        for trade in self.trades:
            day = trade['date'].strftime('%Y-%m-%d')
            if day not in trades_by_day:
                trades_by_day[day] = []
            trades_by_day[day].append(trade)
        
        for day in sorted(trades_by_day.keys()):
            day_trades = trades_by_day[day]
            logger.info(f"   {day}: {len(day_trades)} trades")
            for trade in day_trades:
                logger.info(f"      • {trade['symbol']} {trade['option_type']} @ ${trade['option_price']:.2f} ({trade['contracts']} contracts)")
        
        logger.info(f"")
        
        # Rejection reasons
        logger.info(f"❌ REJECTION REASONS:")
        rejection_reasons = {}
        for reject in self.rejected:
            reason = reject['reason']
            if reason not in rejection_reasons:
                rejection_reasons[reason] = []
            rejection_reasons[reason].append(reject)
        
        for reason, rejects in sorted(rejection_reasons.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info(f"   {reason}: {len(rejects)}")
        
        logger.info(f"")
        
        # Detailed trades
        logger.info(f"📋 DETAILED TRADES:")
        for i, trade in enumerate(self.trades, 1):
            logger.info(f"   {i}. {trade['symbol']} {trade['option_type']}")
            logger.info(f"      Date: {trade['date'].strftime('%Y-%m-%d')}")
            logger.info(f"      Option: {trade['option_symbol']}")
            logger.info(f"      Strike: ${trade['strike']:.2f}, Price: ${trade['option_price']:.2f}")
            logger.info(f"      Contracts: {trade['contracts']}, Total: ${trade['total_cost']:,.2f}")
            logger.info(f"      Expiration: {trade['expiration']} (DTE: {trade['dte']})")
            logger.info(f"      Signal: {trade['direction']} @ {trade['confidence']:.2%} ({trade['agent']})")
            logger.info(f"")
        
        # Save to file
        self.save_report()
    
    def save_report(self):
        """Save detailed report to file"""
        report_file = Path("backtest_results") / f"backtest_dec12_19_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("OPTIONS TRADING BACKTEST REPORT\n")
            f.write(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}\n")
            f.write("="*60 + "\n\n")
            
            f.write("TRADES EXECUTED:\n")
            f.write("-"*60 + "\n")
            for trade in self.trades:
                f.write(f"{trade['date'].strftime('%Y-%m-%d')} | {trade['symbol']} | {trade['option_type']} | ")
                f.write(f"{trade['option_symbol']} | Strike: ${trade['strike']:.2f} | ")
                f.write(f"Price: ${trade['option_price']:.2f} | {trade['contracts']} contracts | ")
                f.write(f"Total: ${trade['total_cost']:,.2f} | DTE: {trade['dte']} | ")
                f.write(f"Signal: {trade['direction']} @ {trade['confidence']:.2%}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("SIGNALS GENERATED:\n")
            f.write("-"*60 + "\n")
            for signal in self.signals:
                f.write(f"{signal['date'].strftime('%Y-%m-%d')} | {signal['symbol']} | ")
                f.write(f"{signal['direction']} @ {signal['confidence']:.2%} | {signal['agent']}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("REJECTED SETUPS:\n")
            f.write("-"*60 + "\n")
            for reject in self.rejected:
                f.write(f"{reject['date'].strftime('%Y-%m-%d')} | {reject['symbol']} | {reject['reason']}\n")
        
        logger.info(f"📄 Report saved to: {report_file}")

def main():
    """Main entry point"""
    # Backtest period: December 12-19, 2025
    start_date = datetime(2025, 12, 12)
    end_date = datetime(2025, 12, 19)
    
    backtester = OptionsBacktester(start_date, end_date)
    backtester.run_backtest()

if __name__ == '__main__':
    main()

