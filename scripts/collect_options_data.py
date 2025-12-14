#!/usr/bin/env python3
"""
Script to collect historical options data from Massive API
Usage:
    python scripts/collect_options_data.py --symbol AAPL --start 2024-01-01 --end 2024-12-31
    python scripts/collect_options_data.py --all-symbols --lookback 252
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.historical_options_collector import HistoricalOptionsCollector
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Collect historical options data')
    parser.add_argument('--symbol', type=str, help='Symbol to collect (e.g., AAPL)')
    parser.add_argument('--all-symbols', action='store_true', help='Collect for all configured symbols')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--lookback', type=int, default=252, help='Lookback days (default: 252)')
    parser.add_argument('--expiration-dates', type=str, nargs='+', help='Specific expiration dates (YYYY-MM-DD)')
    parser.add_argument('--days-step', type=int, default=1, help='Collect every N days (default: 1)')
    parser.add_argument('--rl-training', action='store_true', help='Collect data optimized for RL training')
    
    args = parser.parse_args()
    
    # Check API key
    if not Config.MASSIVE_API_KEY:
        logger.error("MASSIVE_API_KEY not set in environment variables")
        logger.error("Please set it in .env file: MASSIVE_API_KEY=your_key")
        return 1
    
    collector = HistoricalOptionsCollector()
    
    if not collector.feed.is_available():
        logger.error("Massive API not available")
        return 1
    
    # Determine symbols
    if args.all_symbols:
        symbols = Config.TICKERS
        logger.info(f"Collecting for all symbols: {symbols}")
    elif args.symbol:
        symbols = [args.symbol]
    else:
        logger.error("Must specify --symbol or --all-symbols")
        return 1
    
    # Determine dates
    if args.rl_training:
        # Use lookback
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.lookback)).strftime('%Y-%m-%d')
        logger.info(f"RL training mode: {args.lookback} days lookback")
    elif args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        logger.error("Must specify --start and --end, or use --rl-training")
        return 1
    
    # Collect data
    try:
        if args.rl_training:
            results = collector.collect_for_rl_training(
                symbols,
                lookback_days=args.lookback,
                expiration_dates=args.expiration_dates
            )
        else:
            results = collector.collect_multiple_symbols(
                symbols,
                start_date,
                end_date,
                expiration_dates=args.expiration_dates,
                days_step=args.days_step
            )
        
        # Print summary
        print("\n" + "="*60)
        print("Collection Summary")
        print("="*60)
        
        if isinstance(results, dict) and 'summary' in results:
            summary = results['summary']
            print(f"Symbols: {summary['symbols']}")
            print(f"Total dates: {summary['total_dates']}")
            print(f"Total contracts: {summary['total_contracts']}")
            print(f"Date range: {summary['start_date']} to {summary['end_date']}")
        else:
            for symbol, stats in results.items():
                print(f"\n{symbol}:")
                print(f"  Dates collected: {stats.get('dates_collected', 0)}")
                print(f"  Total contracts: {stats.get('total_contracts', 0)}")
                print(f"  Errors: {stats.get('errors', 0)}")
        
        print("\n✅ Collection complete!")
        print(f"Data stored in: data/options_history.db")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())

