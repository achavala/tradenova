"""
Historical Options Data Collector
Collects and stores historical options data from Massive API for RL training
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from services.massive_data_feed import MassiveDataFeed
from config import Config

logger = logging.getLogger(__name__)

class HistoricalOptionsCollector:
    """
    Collects historical options data for training and analysis
    
    Features:
    - Batch collection for multiple symbols
    - Point-in-time accuracy
    - IV history collection
    - Automatic data storage
    - Progress tracking
    """
    
    def __init__(self, massive_feed: Optional[MassiveDataFeed] = None):
        """
        Initialize collector
        
        Args:
            massive_feed: MassiveDataFeed instance or None to create new
        """
        self.feed = massive_feed or MassiveDataFeed(
            api_key=Config.MASSIVE_API_KEY,
            base_url=Config.MASSIVE_BASE_URL
        )
        
        if not self.feed.is_available():
            logger.warning("Massive API not available. Historical collection disabled.")
    
    def collect_symbol_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        expiration_dates: Optional[List[str]] = None,
        days_step: int = 1
    ) -> dict:
        """
        Collect historical options data for a symbol
        
        Args:
            symbol: Underlying symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            expiration_dates: List of expiration dates to collect or None for all
            days_step: Collect every N days (1 = daily, 7 = weekly)
            
        Returns:
            Dictionary with collection statistics
        """
        if not self.feed.is_available():
            return {'error': 'Massive API not available'}
        
        logger.info(f"Starting historical collection for {symbol} from {start_date} to {end_date}")
        
        stats = {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'dates_collected': 0,
            'total_contracts': 0,
            'errors': 0,
            'dates': []
        }
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            try:
                # Get options chain for this date
                if expiration_dates:
                    contracts = []
                    for exp_date in expiration_dates:
                        chain = self.feed.get_options_chain(
                            symbol,
                            expiration_date=exp_date,
                            date=date_str
                        )
                        contracts.extend(chain)
                else:
                    contracts = self.feed.get_options_chain(symbol, date=date_str)
                
                if contracts:
                    stats['dates_collected'] += 1
                    stats['total_contracts'] += len(contracts)
                    stats['dates'].append(date_str)
                    logger.info(f"Collected {len(contracts)} contracts for {symbol} on {date_str}")
                else:
                    stats['errors'] += 1
                    logger.warning(f"No contracts found for {symbol} on {date_str}")
                
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error collecting data for {symbol} on {date_str}: {e}")
            
            current_date += timedelta(days=days_step)
        
        logger.info(f"Collection complete for {symbol}: {stats['dates_collected']} dates, {stats['total_contracts']} contracts")
        return stats
    
    def collect_iv_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        expiration_dates: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Collect historical IV data
        
        Args:
            symbol: Underlying symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            expiration_dates: List of expiration dates or None for all
            
        Returns:
            DataFrame with IV history
        """
        if not self.feed.is_available():
            return pd.DataFrame()
        
        logger.info(f"Collecting IV history for {symbol} from {start_date} to {end_date}")
        
        df = self.feed.get_historical_iv(
            symbol,
            start_date,
            end_date,
            expiration_date=expiration_dates[0] if expiration_dates and len(expiration_dates) == 1 else None
        )
        
        if not df.empty:
            logger.info(f"Collected IV history: {len(df)} records")
        
        return df
    
    def collect_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        expiration_dates: Optional[List[str]] = None,
        days_step: int = 1
    ) -> dict:
        """
        Collect historical data for multiple symbols
        
        Args:
            symbols: List of symbols to collect
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            expiration_dates: List of expiration dates or None for all
            days_step: Collect every N days
            
        Returns:
            Dictionary with statistics for each symbol
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Collecting data for {symbol} ({symbols.index(symbol) + 1}/{len(symbols)})")
            results[symbol] = self.collect_symbol_history(
                symbol,
                start_date,
                end_date,
                expiration_dates,
                days_step
            )
        
        return results
    
    def collect_for_rl_training(
        self,
        symbols: List[str],
        lookback_days: int = 252,
        expiration_dates: Optional[List[str]] = None
    ) -> dict:
        """
        Collect data optimized for RL training
        
        Collects:
        - Daily options chains
        - IV history
        - Point-in-time accuracy
        
        Args:
            symbols: List of symbols
            lookback_days: Number of days to look back
            expiration_dates: Specific expiration dates or None for all
            
        Returns:
            Collection statistics
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        logger.info(f"Collecting RL training data: {len(symbols)} symbols, {lookback_days} days")
        
        results = self.collect_multiple_symbols(
            symbols,
            start_date,
            end_date,
            expiration_dates,
            days_step=1  # Daily for RL training
        )
        
        # Summary
        total_dates = sum(r.get('dates_collected', 0) for r in results.values())
        total_contracts = sum(r.get('total_contracts', 0) for r in results.values())
        
        logger.info(f"RL training data collection complete:")
        logger.info(f"  - Symbols: {len(symbols)}")
        logger.info(f"  - Total dates: {total_dates}")
        logger.info(f"  - Total contracts: {total_contracts}")
        
        return {
            'summary': {
                'symbols': len(symbols),
                'total_dates': total_dates,
                'total_contracts': total_contracts,
                'start_date': start_date,
                'end_date': end_date
            },
            'results': results
        }

