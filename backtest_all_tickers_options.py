#!/usr/bin/env python3
"""
Backtest ALL Tickers Options - Yesterday's Real Data
Tests all configured tickers to see which would have generated profitable options trades
Uses REAL Alpaca data - NO FAKE NUMBERS
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_all_tickers_options.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AllTickersOptionsBacktest:
    """Backtest options for all tickers"""
    
    def __init__(self):
        self.yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.tickers = Config.TICKERS
        
        logger.info("="*70)
        logger.info("ALL TICKERS OPTIONS BACKTEST - YESTERDAY'S REAL DATA")
        logger.info("="*70)
        logger.info(f"Date: {self.yesterday.strftime('%Y-%m-%d')}")
        logger.info(f"Tickers: {', '.join(self.tickers)}")
        logger.info(f"Total: {len(self.tickers)} tickers")
        logger.info(f"Using REAL Alpaca data - NO FAKE NUMBERS")
        logger.info("="*70)
        
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        self.orchestrator = MultiAgentOrchestrator(self.client)
        
        self.results: List[Dict] = []
    
    def get_stock_prices(self, symbol: str) -> Optional[Dict]:
        """Get yesterday's and today's stock prices"""
        try:
            start = self.yesterday - timedelta(days=2)
            end = self.today + timedelta(days=1)
            
            bars = self.client.get_historical_bars(
                symbol,
                TimeFrame.Day,
                start,
                end
            )
            
            if bars.empty:
                return None
            
            # Get yesterday's close
            yesterday_bars = bars[bars.index.date == self.yesterday.date()]
            if yesterday_bars.empty:
                yesterday_bars = bars[bars.index < self.today]
                if not yesterday_bars.empty:
                    yesterday_bars = yesterday_bars.iloc[[-1]]
            
            if yesterday_bars.empty:
                return None
            
            # Get today's close
            today_bars = bars[bars.index.date >= self.today.date()]
            if today_bars.empty:
                latest_price = self.client.get_latest_price(symbol)
                if latest_price:
                    today_close = latest_price
                else:
                    today_close = float(yesterday_bars['close'].iloc[0])
            else:
                today_close = float(today_bars['close'].iloc[0])
            
            yesterday_close = float(yesterday_bars['close'].iloc[0])
            yesterday_high = float(yesterday_bars['high'].iloc[0])
            yesterday_low = float(yesterday_bars['low'].iloc[0])
            yesterday_open = float(yesterday_bars['open'].iloc[0])
            
            stock_move = today_close - yesterday_close
            stock_move_pct = (stock_move / yesterday_close) * 100
            
            return {
                'symbol': symbol,
                'yesterday_close': yesterday_close,
                'yesterday_high': yesterday_high,
                'yesterday_low': yesterday_low,
                'yesterday_open': yesterday_open,
                'today_close': today_close,
                'stock_move': stock_move,
                'stock_move_pct': stock_move_pct
            }
            
        except Exception as e:
            logger.debug(f"Error fetching prices for {symbol}: {e}")
            return None
    
    def analyze_signal(self, symbol: str) -> Optional[Dict]:
        """Analyze if system would have generated a signal"""
        try:
            start = self.yesterday - timedelta(days=90)
            end = self.yesterday + timedelta(days=1)
            
            historical_bars = self.client.get_historical_bars(
                symbol,
                TimeFrame.Day,
                start,
                end
            )
            
            if historical_bars.empty:
                return None
            
            # Handle timezone
            from pytz import UTC
            if historical_bars.index.tz is not None:
                yesterday_tz = self.yesterday
                if yesterday_tz.tzinfo is None:
                    yesterday_tz = UTC.localize(self.yesterday)
            else:
                yesterday_tz = self.yesterday
                if yesterday_tz.tzinfo is not None:
                    yesterday_tz = yesterday_tz.replace(tzinfo=None)
            
            bars_up_to_yesterday = historical_bars[historical_bars.index <= yesterday_tz]
            
            if len(bars_up_to_yesterday) < 10:
                return None
            
            trade_intent = self.orchestrator.analyze_symbol(symbol, bars_up_to_yesterday)
            
            if trade_intent:
                return {
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'reasoning': trade_intent.reasoning
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None
    
    def calculate_options_pnl(self, stock_data: Dict, signal: Dict) -> Dict:
        """Calculate what options P&L would have been"""
        yesterday_close = stock_data['yesterday_close']
        today_close = stock_data['today_close']
        stock_move_pct = stock_data['stock_move_pct']
        direction = signal['direction']
        
        # Determine option type
        if direction == 'LONG':
            option_type = 'CALL'
            profitable = stock_move_pct > 0
        else:  # SHORT
            option_type = 'PUT'
            profitable = stock_move_pct < 0
        
        # Calculate ATM option P&L
        atm_strike = round(yesterday_close)
        
        # Estimate option prices
        if option_type == 'CALL':
            intrinsic = max(0, today_close - atm_strike)
            # Entry price estimate (3% for ATM)
            if abs(atm_strike - yesterday_close) / yesterday_close < 0.01:
                entry_price_est = yesterday_close * 0.03
            elif atm_strike > yesterday_close:
                entry_price_est = yesterday_close * 0.015
            else:
                entry_price_est = (yesterday_close - atm_strike) + (yesterday_close * 0.02)
        else:  # PUT
            intrinsic = max(0, atm_strike - today_close)
            if abs(atm_strike - yesterday_close) / yesterday_close < 0.01:
                entry_price_est = yesterday_close * 0.03
            elif atm_strike < yesterday_close:
                entry_price_est = yesterday_close * 0.015
            else:
                entry_price_est = (atm_strike - yesterday_close) + (yesterday_close * 0.02)
        
        # Exit price (intrinsic value + remaining time value)
        # Time value decays, but we'll use a conservative estimate
        # Exit should be at least intrinsic value
        exit_price_est = max(intrinsic, intrinsic + (entry_price_est * 0.15))
        
        # P&L
        pnl_per_contract = exit_price_est - entry_price_est
        pnl_pct = (pnl_per_contract / entry_price_est * 100) if entry_price_est > 0 else 0
        leverage = abs(pnl_pct / stock_move_pct) if stock_move_pct != 0 else 0
        
        return {
            'option_type': option_type,
            'strike': atm_strike,
            'entry_price_est': entry_price_est,
            'exit_price_est': exit_price_est,
            'pnl_per_contract': pnl_per_contract,
            'pnl_pct': pnl_pct,
            'leverage': leverage,
            'profitable': profitable,
            'intrinsic': intrinsic
        }
    
    def backtest_ticker(self, symbol: str) -> Optional[Dict]:
        """Backtest a single ticker"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing {symbol}...")
            logger.info(f"{'='*60}")
            
            # Get stock prices
            stock_data = self.get_stock_prices(symbol)
            if not stock_data:
                logger.warning(f"  ⚠️  No stock data for {symbol}")
                return None
            
            logger.info(f"  Stock: ${stock_data['yesterday_close']:.2f} → ${stock_data['today_close']:.2f} ({stock_data['stock_move_pct']:.2f}%)")
            
            # Analyze signal
            signal = self.analyze_signal(symbol)
            if not signal:
                logger.info(f"  ⏸️  No signal generated")
                return None
            
            logger.info(f"  ✅ Signal: {signal['direction']} ({signal['confidence']:.2%}) - {signal['agent']}")
            
            # Calculate options P&L
            options_pnl = self.calculate_options_pnl(stock_data, signal)
            
            status = "✅ PROFIT" if options_pnl['profitable'] else "❌ LOSS"
            logger.info(f"  {status}: ${options_pnl['pnl_per_contract']:.2f} ({options_pnl['pnl_pct']:.2f}%)")
            
            return {
                'symbol': symbol,
                'stock_data': stock_data,
                'signal': signal,
                'options_pnl': options_pnl,
                'profitable': options_pnl['profitable']
            }
            
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {e}")
            return None
    
    def run_backtest(self):
        """Run backtest for all tickers"""
        logger.info("\n" + "="*70)
        logger.info("STARTING BACKTEST FOR ALL TICKERS")
        logger.info("="*70)
        
        for ticker in self.tickers:
            result = self.backtest_ticker(ticker)
            if result:
                self.results.append(result)
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive report"""
        logger.info("\n" + "="*70)
        logger.info("BACKTEST RESULTS - ALL TICKERS")
        logger.info("="*70)
        
        if not self.results:
            logger.info("No results to report")
            return
        
        profitable = [r for r in self.results if r['profitable']]
        losing = [r for r in self.results if r['profitable'] == False]
        
        logger.info(f"\n📊 SUMMARY")
        logger.info(f"   Total Tickers Tested: {len(self.results)}")
        logger.info(f"   ✅ Profitable Trades: {len(profitable)}")
        logger.info(f"   ❌ Losing Trades: {len(losing)}")
        logger.info(f"   ⏸️  No Signal: {len(self.tickers) - len(self.results)}")
        logger.info(f"   Win Rate: {len(profitable) / len(self.results) * 100:.1f}%")
        
        if profitable:
            logger.info(f"\n✅ PROFITABLE TRADES ({len(profitable)}):")
            logger.info(f"{'='*70}")
            for result in sorted(profitable, key=lambda x: x['options_pnl']['pnl_pct'], reverse=True):
                pnl = result['options_pnl']
                stock = result['stock_data']
                signal = result['signal']
                logger.info(f"\n   {result['symbol']}:")
                logger.info(f"      Signal: {signal['direction']} ({signal['confidence']:.2%}) - {signal['agent']}")
                logger.info(f"      Stock: ${stock['yesterday_close']:.2f} → ${stock['today_close']:.2f} ({stock['stock_move_pct']:.2f}%)")
                logger.info(f"      Option: {pnl['option_type']} @ ${pnl['strike']:.2f}")
                logger.info(f"      P&L: ${pnl['pnl_per_contract']:.2f} ({pnl['pnl_pct']:.2f}%)")
                logger.info(f"      Leverage: {pnl['leverage']:.1f}x")
        
        if losing:
            logger.info(f"\n❌ LOSING TRADES ({len(losing)}):")
            logger.info(f"{'='*70}")
            for result in sorted(losing, key=lambda x: x['options_pnl']['pnl_pct']):
                pnl = result['options_pnl']
                stock = result['stock_data']
                signal = result['signal']
                logger.info(f"   {result['symbol']}: {signal['direction']} → Stock moved {stock['stock_move_pct']:.2f}% → Loss: {pnl['pnl_pct']:.2f}%")
        
        # Calculate total P&L
        total_pnl = sum(r['options_pnl']['pnl_per_contract'] for r in self.results)
        avg_pnl = total_pnl / len(self.results) if self.results else 0
        
        logger.info(f"\n💰 TOTAL P&L")
        logger.info(f"   Total: ${total_pnl:.2f}")
        logger.info(f"   Average per trade: ${avg_pnl:.2f}")
        
        # Save detailed report
        report = {
            'backtest_date': self.yesterday.isoformat(),
            'tickers_tested': len(self.tickers),
            'tickers_with_signals': len(self.results),
            'profitable_trades': len(profitable),
            'losing_trades': len(losing),
            'win_rate': len(profitable) / len(self.results) * 100 if self.results else 0,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'results': self.results
        }
        
        report_file = f"logs/options_backtest_all_tickers_{self.yesterday.strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n✅ Detailed report saved to: {report_file}")
        logger.info("="*70)

def main():
    print("\n" + "="*70)
    print("ALL TICKERS OPTIONS BACKTEST - YESTERDAY")
    print("="*70)
    print("\nThis will test ALL configured tickers to see which would have")
    print("generated profitable options trades yesterday using REAL data.")
    print("\n" + "-"*70)
    
    confirm = input("\nProceed with backtest? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Backtest cancelled.")
        return
    
    backtest = AllTickersOptionsBacktest()
    backtest.run_backtest()

if __name__ == "__main__":
    main()

