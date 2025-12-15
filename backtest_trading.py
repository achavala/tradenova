#!/usr/bin/env python3
"""
Backtesting Engine - Real Historical Data
Allows selecting tickers and date ranges for backtesting with real Alpaca data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from alpaca_trade_api.rest import TimeFrame
import json

from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.risk.profit_manager import ProfitManager
from core.risk.advanced_risk_manager import AdvancedRiskManager
from core.live.broker_executor import BrokerExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BacktestEngine:
    """Backtesting engine with real historical data"""
    
    def __init__(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_balance: float = 100000.0
    ):
        """
        Initialize backtest engine
        
        Args:
            tickers: List of ticker symbols to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Starting capital
        """
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # Initialize clients
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        self.orchestrator = MultiAgentOrchestrator(self.client)
        self.profit_manager = ProfitManager(
            tp1_pct=0.10,  # 10% for testing
            tp1_exit_pct=1.00,
            stop_loss_pct=0.05  # 5% stop loss
        )
        self.risk_manager = AdvancedRiskManager(
            initial_balance=initial_balance,
            daily_loss_limit_pct=0.10,
            max_drawdown_pct=0.20,
            max_loss_streak=5
        )
        
        # Track positions and trades
        self.positions: Dict[str, Dict] = {}
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.daily_pnl: List[Dict] = []
        
        # Historical data cache
        self.historical_data: Dict[str, pd.DataFrame] = {}
        
    def fetch_historical_data(self) -> bool:
        """Fetch real historical data from Alpaca"""
        logger.info("="*70)
        logger.info("FETCHING REAL HISTORICAL DATA FROM ALPACA")
        logger.info("="*70)
        logger.info(f"Tickers: {', '.join(self.tickers)}")
        logger.info(f"Date Range: {self.start_date.date()} to {self.end_date.date()}")
        logger.info("="*70)
        
        try:
            for ticker in self.tickers:
                logger.info(f"Fetching data for {ticker}...")
                
                # Fetch 1-minute bars for the date range
                # Note: Alpaca may limit historical data, so we'll use daily bars for backtesting
                # which are more reliable and available for longer periods
                bars = self.client.get_historical_bars(
                    ticker,
                    TimeFrame.Day,  # Use daily bars for backtesting (more reliable)
                    self.start_date,
                    self.end_date
                )
                
                if bars.empty:
                    logger.warning(f"No data available for {ticker}")
                    continue
                
                # Ensure proper datetime index
                if not isinstance(bars.index, pd.DatetimeIndex):
                    if 'timestamp' in bars.columns:
                        bars['timestamp'] = pd.to_datetime(bars['timestamp'])
                        bars.set_index('timestamp', inplace=True)
                
                # Sort by time
                bars.sort_index(inplace=True)
                
                self.historical_data[ticker] = bars
                logger.info(f"✅ {ticker}: {len(bars)} bars from {bars.index[0]} to {bars.index[-1]}")
            
            total_bars = sum(len(df) for df in self.historical_data.values())
            logger.info(f"\n✅ Total bars fetched: {total_bars}")
            logger.info(f"✅ Data coverage: {len(self.historical_data)}/{len(self.tickers)} tickers")
            
            return len(self.historical_data) > 0
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}", exc_info=True)
            return False
    
    def get_current_price(self, ticker: str, current_time: datetime) -> Optional[float]:
        """Get price at a specific time"""
        if ticker not in self.historical_data:
            return None
        
        df = self.historical_data[ticker]
        
        # Find the bar at or before current_time
        mask = df.index <= current_time
        if not mask.any():
            return None
        
        latest_bar = df[mask].iloc[-1]
        return float(latest_bar['close'])
    
    def update_positions(self, current_time: datetime):
        """Update positions and check profit targets/stop loss"""
        for symbol, position in list(self.positions.items()):
            current_price = self.get_current_price(symbol, current_time)
            if not current_price:
                continue
            
            entry_price = position['entry_price']
            qty = position['qty']
            side = position['side']
            
            # Calculate P&L
            if side == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            position['current_price'] = current_price
            position['pnl_pct'] = pnl_pct
            position['unrealized_pnl'] = (current_price - entry_price) * qty * (1 if side == 'long' else -1)
            
            # Check profit target (10%)
            if pnl_pct >= 10.0:
                self.close_position(symbol, current_time, 'profit_target', current_price)
            
            # Check stop loss (5%)
            elif pnl_pct <= -5.0:
                self.close_position(symbol, current_time, 'stop_loss', current_price)
    
    def close_position(self, symbol: str, current_time: datetime, reason: str, exit_price: float):
        """Close a position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        qty = position['qty']
        side = position['side']
        
        # Calculate P&L
        if side == 'long':
            pnl = (exit_price - entry_price) * qty
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl = (entry_price - exit_price) * qty
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        # Record trade
        trade = {
            'symbol': symbol,
            'entry_time': position['entry_time'],
            'exit_time': current_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'qty': qty,
            'side': side,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'agent': position.get('agent', 'Unknown')
        }
        self.trades.append(trade)
        
        # Update balance
        self.current_balance += pnl
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"✅ Closed {symbol}: {side} {qty} @ ${exit_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:.2f}%) | Reason: {reason}")
    
    def execute_trade(self, symbol: str, signal: Dict, current_time: datetime, current_price: float):
        """Execute a trade entry"""
        # Check if we can open new position
        max_positions = 10
        if len(self.positions) >= max_positions:
            logger.debug(f"{symbol}: Cannot open position - max positions ({max_positions}) reached")
            return False
        
        # Allow multiple positions per ticker to reach 2-5 trades/day target
        # Only check if we have too many total positions (already checked above)
        # Removed: if symbol in self.positions: return False
        
        # Calculate position size (10% of balance per position)
        position_value = self.current_balance * 0.10
        qty = int(position_value / current_price)
        
        if qty < 1:
            return False
        
        # Determine side
        side = 'long' if signal['direction'] == 'LONG' else 'short'
        
        # Create position
        self.positions[symbol] = {
            'qty': qty,
            'entry_price': current_price,
            'side': side,
            'entry_time': current_time,
            'agent': signal.get('agent', 'Unknown'),
            'current_price': current_price,
            'pnl_pct': 0.0,
            'unrealized_pnl': 0.0
        }
        
        logger.info(f"📈 Opened {symbol}: {side} {qty} @ ${current_price:.2f} | Balance: ${self.current_balance:,.2f}")
        return True
    
    def run_backtest(self):
        """Run the backtest"""
        logger.info("\n" + "="*70)
        logger.info("STARTING BACKTEST")
        logger.info("="*70)
        
        # Fetch historical data
        if not self.fetch_historical_data():
            logger.error("Failed to fetch historical data")
            return
        
        # Get all unique timestamps across all tickers
        all_times = set()
        for df in self.historical_data.values():
            all_times.update(df.index)
        
        all_times = sorted(list(all_times))
        
        logger.info(f"\nProcessing {len(all_times)} time steps...")
        logger.info(f"Date range: {all_times[0]} to {all_times[-1]}")
        
        # Process each time step
        last_trade_check = {}
        # For daily bars, check once per day. For minute bars, check every 5 minutes
        # We'll determine based on the timeframe of the data
        if len(all_times) > 0:
            time_diff = all_times[1] - all_times[0] if len(all_times) > 1 else timedelta(days=1)
            if time_diff >= timedelta(days=1):
                check_interval = timedelta(days=1)  # Daily bars
            else:
                check_interval = timedelta(minutes=5)  # Minute bars
        else:
            check_interval = timedelta(days=1)
        
        # Track warmup mode
        warmup_count = 0
        trading_count = 0
        
        for i, current_time in enumerate(all_times):
            # Update existing positions
            self.update_positions(current_time)
            
            # Determine if we're in warmup mode or trading mode
            # Warmup: Need 50+ bars for feature calculation, but don't trade yet
            # Trading: Have enough data AND we're in the trading window
            is_warmup = False
            can_trade = False
            
            # Check if we have enough data for analysis
            sample_ticker = self.tickers[0] if self.tickers else None
            if sample_ticker and sample_ticker in self.historical_data:
                df_sample = self.historical_data[sample_ticker]
                bars_up_to_now_sample = df_sample[df_sample.index <= current_time]
                if len(bars_up_to_now_sample) < 50:
                    is_warmup = True
                else:
                    # We have enough data - check if we're in trading window
                    # If start_date is set for warmup, only trade after warmup period
                    # For now, trade once we have enough data
                    can_trade = True
            
            # Check for new trade opportunities (every 5 minutes)
            for ticker in self.tickers:
                if ticker not in self.historical_data:
                    continue
                
                # Allow multiple positions per ticker to reach 2-5 trades/day target
                # Skip only if we have too many total positions
                if len(self.positions) >= 10:  # Max 10 total positions
                    continue
                
                # Check if it's time to evaluate
                if ticker in last_trade_check:
                    if current_time - last_trade_check[ticker] < check_interval:
                        continue
                
                last_trade_check[ticker] = current_time
                
                # Get bars up to current time
                df = self.historical_data[ticker]
                bars_up_to_now = df[df.index <= current_time]
                
                # Warmup mode: Not enough data yet
                if len(bars_up_to_now) < 50:
                    if i == 0 or (i % 10 == 0):  # Log occasionally
                        warmup_count += 1
                        logger.info(f"WARMUP MODE: {ticker} - {len(bars_up_to_now)} / 50 bars available — trading disabled")
                    continue
                
                # Log transition to trading mode (first time we have enough data)
                if warmup_count > 0 and trading_count == 0:
                    logger.info(f"✅ WARMUP COMPLETE: {ticker} - {len(bars_up_to_now)} bars available — trading enabled")
                
                # Trading mode: Have enough data
                if not can_trade:
                    continue  # Skip if warmup mode
                
                trading_count += 1
                
                # Get current price
                current_price = self.get_current_price(ticker, current_time)
                if not current_price:
                    continue
                
                # Analyze with orchestrator
                try:
                    trade_intent = self.orchestrator.analyze_symbol(ticker, bars_up_to_now)
                    
                    if trade_intent:
                        logger.debug(f"{ticker} at {current_time.date()}: Signal from {trade_intent.agent_name} "
                                   f"with confidence {trade_intent.confidence:.2f}")
                        
                        if trade_intent.confidence >= 0.20:  # Lowered from 0.30 to get 2-5 trades/day
                            # Log warmup transition if this is first trade
                            if trading_count == 1:
                                logger.info(f"✅ WARMUP COMPLETE: {len(bars_up_to_now)} bars available — trading enabled")
                            # Create signal dict
                            signal = {
                                'direction': trade_intent.direction.value,
                                'confidence': trade_intent.confidence,
                                'agent': trade_intent.agent_name,
                                'reasoning': trade_intent.reasoning
                            }
                            
                            # Execute trade
                            executed = self.execute_trade(ticker, signal, current_time, current_price)
                            if not executed:
                                logger.debug(f"{ticker}: Trade not executed (check execute_trade logic)")
                        else:
                            logger.debug(f"{ticker}: Signal confidence {trade_intent.confidence:.2f} < 0.20 threshold")
                    else:
                        logger.debug(f"{ticker} at {current_time.date()}: No signal generated")
                        
                except Exception as e:
                    logger.debug(f"Error analyzing {ticker} at {current_time}: {e}")
                    continue
            
            # Record equity curve (every hour)
            if i % 60 == 0 or i == len(all_times) - 1:
                total_value = self.current_balance
                for pos in self.positions.values():
                    total_value += pos.get('unrealized_pnl', 0)
                
                self.equity_curve.append({
                    'timestamp': current_time,
                    'equity': total_value,
                    'balance': self.current_balance,
                    'positions': len(self.positions)
                })
        
        # Close all remaining positions at end
        logger.info("\nClosing all remaining positions at end of backtest...")
        final_time = all_times[-1]
        for symbol in list(self.positions.keys()):
            final_price = self.get_current_price(symbol, final_time)
            if final_price:
                self.close_position(symbol, final_time, 'end_of_backtest', final_price)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate backtest report"""
        logger.info("\n" + "="*70)
        logger.info("BACKTEST RESULTS")
        logger.info("="*70)
        
        # Calculate metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Drawdown calculation
        peak = self.initial_balance
        max_drawdown = 0
        for point in self.equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            drawdown = ((peak - point['equity']) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Print report
        logger.info(f"\n📊 PERFORMANCE METRICS")
        logger.info(f"{'='*70}")
        logger.info(f"Initial Balance:     ${self.initial_balance:,.2f}")
        logger.info(f"Final Balance:       ${self.current_balance:,.2f}")
        logger.info(f"Total Return:        {total_return:.2f}%")
        logger.info(f"Total P&L:          ${total_pnl:,.2f}")
        logger.info(f"Max Drawdown:        {max_drawdown:.2f}%")
        logger.info(f"\n📈 TRADE STATISTICS")
        logger.info(f"{'='*70}")
        logger.info(f"Total Trades:        {total_trades}")
        logger.info(f"Winning Trades:      {len(winning_trades)}")
        logger.info(f"Losing Trades:       {len(losing_trades)}")
        logger.info(f"Win Rate:            {win_rate:.2f}%")
        logger.info(f"Average Win:         ${avg_win:,.2f}")
        logger.info(f"Average Loss:        ${avg_loss:,.2f}")
        logger.info(f"Profit Factor:       {abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else 'N/A'}")
        
        # Trades by symbol
        logger.info(f"\n📋 TRADES BY SYMBOL")
        logger.info(f"{'='*70}")
        symbol_stats = {}
        for trade in self.trades:
            symbol = trade['symbol']
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {'count': 0, 'pnl': 0, 'wins': 0}
            symbol_stats[symbol]['count'] += 1
            symbol_stats[symbol]['pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                symbol_stats[symbol]['wins'] += 1
        
        for symbol, stats in sorted(symbol_stats.items()):
            win_rate_sym = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
            logger.info(f"{symbol:6s}: {stats['count']:3d} trades | ${stats['pnl']:8,.2f} P&L | {win_rate_sym:.1f}% win rate")
        
        # Save detailed results - convert all datetime objects to strings
        serialized_trades = []
        for trade in self.trades:
            serialized_trade = trade.copy()
            # Convert datetime objects to ISO format strings
            if 'entry_time' in serialized_trade and serialized_trade['entry_time']:
                if hasattr(serialized_trade['entry_time'], 'isoformat'):
                    serialized_trade['entry_time'] = serialized_trade['entry_time'].isoformat()
                elif isinstance(serialized_trade['entry_time'], str):
                    pass  # Already a string
            if 'exit_time' in serialized_trade and serialized_trade['exit_time']:
                if hasattr(serialized_trade['exit_time'], 'isoformat'):
                    serialized_trade['exit_time'] = serialized_trade['exit_time'].isoformat()
                elif isinstance(serialized_trade['exit_time'], str):
                    pass  # Already a string
            serialized_trades.append(serialized_trade)
        
        results = {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'tickers': self.tickers,
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'total_return_pct': total_return,
            'total_pnl': total_pnl,
            'max_drawdown_pct': max_drawdown,
            'total_trades': total_trades,
            'win_rate_pct': win_rate,
            'trades': serialized_trades,
            'equity_curve': [
                {
                    'timestamp': point['timestamp'].isoformat() if hasattr(point['timestamp'], 'isoformat') else str(point['timestamp']),
                    'equity': float(point['equity']),
                    'balance': float(point['balance']),
                    'positions': int(point['positions'])
                }
                for point in self.equity_curve
            ]
        }
        
        results_file = f"logs/backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n✅ Detailed results saved to: {results_file}")
        logger.info("="*70)

def main():
    """Main function with interactive ticker and date selection"""
    print("\n" + "="*70)
    print("TRADENOVA BACKTESTING ENGINE")
    print("="*70)
    print("\nAvailable tickers:")
    print("  NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, MSTR, AVGO, PLTR, AMD, INTC")
    print("\n" + "-"*70)
    
    # Get tickers
    print("\nEnter tickers to backtest (comma-separated, e.g., NVDA,AAPL,TSLA):")
    ticker_input = input("Tickers: ").strip().upper()
    tickers = [t.strip() for t in ticker_input.split(',') if t.strip()]
    
    if not tickers:
        print("No tickers selected. Using default: NVDA, AAPL, TSLA")
        tickers = ['NVDA', 'AAPL', 'TSLA']
    
    # Get date range (default: last 3 months)
    print("\nDate range (default: last 3 months):")
    print("  Press Enter to use last 3 months")
    print("  Or enter custom dates (format: YYYY-MM-DD)")
    
    end_date_input = input("End date (default: today): ").strip()
    if end_date_input:
        try:
            end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
        except:
            print("Invalid date format. Using today.")
            end_date = datetime.now()
    else:
        end_date = datetime.now()
    
    start_date_input = input("Start date (default: 3 months ago): ").strip()
    if start_date_input:
        try:
            start_date = datetime.strptime(start_date_input, '%Y-%m-%d')
        except:
            print("Invalid date format. Using 3 months ago.")
            start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=90)
    
    # Initial balance
    balance_input = input("\nInitial balance (default: $100,000): ").strip()
    initial_balance = float(balance_input) if balance_input else 100000.0
    
    # Confirm
    print("\n" + "="*70)
    print("BACKTEST CONFIGURATION")
    print("="*70)
    print(f"Tickers:        {', '.join(tickers)}")
    print(f"Start Date:    {start_date.date()}")
    print(f"End Date:      {end_date.date()}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print("="*70)
    
    confirm = input("\nProceed with backtest? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Backtest cancelled.")
        return
    
    # Run backtest
    engine = BacktestEngine(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance
    )
    
    engine.run_backtest()

if __name__ == "__main__":
    main()

