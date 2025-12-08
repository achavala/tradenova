"""
Options Selection Logger
Stores selection reasoning trails and metadata for debugging, ML training, and optimization
"""
import logging
import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SelectionLogger:
    """Logs option selection events with full reasoning trails"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize selection logger
        
        Args:
            log_dir: Directory to store logs (default: logs/options_selections/)
        """
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / 'logs' / 'options_selections'
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON log file (one per day)
        today = datetime.now().strftime('%Y-%m-%d')
        self.json_log_file = self.log_dir / f'selections_{today}.jsonl'
        
        logger.info(f"Selection logger initialized: {self.log_dir}")
    
    def log_selection(
        self,
        ticker: str,
        side: str,
        current_price: float,
        selected_option: Optional[Dict],
        selection_time_ms: int,
        market_open: bool,
        max_price: float,
        filter_stats: Dict,
        reasoning: Optional[Dict] = None
    ):
        """
        Log an option selection event
        
        Args:
            ticker: Stock symbol
            side: 'buy' or 'sell'
            current_price: Current stock price
            selected_option: Selected option dict (or None if no selection)
            selection_time_ms: Selection time in milliseconds
            market_open: Whether market was open
            max_price: Dynamic max price used
            filter_stats: Filter statistics
            reasoning: Optional reasoning dict
        """
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker,
                'side': side,
                'current_price': current_price,
                'market_open': market_open,
                'selection_time_ms': selection_time_ms,
                'max_price': max_price,
                'selected': selected_option is not None,
                'filter_stats': filter_stats
            }
            
            if selected_option:
                log_entry['option'] = {
                    'symbol': selected_option.get('symbol'),
                    'strike': selected_option.get('strike'),
                    'expiry': str(selected_option.get('expiry')) if selected_option.get('expiry') else None,
                    'dte': selected_option.get('dte'),
                    'type': selected_option.get('type'),
                    'price': selected_option.get('price'),
                    'bid': selected_option.get('bid'),
                    'ask': selected_option.get('ask'),
                    'spread_pct': selected_option.get('spread_pct'),
                    'volume': selected_option.get('volume'),
                    'open_interest': selected_option.get('open_interest'),
                    'strike_distance_pct': selected_option.get('strike_distance', 0) * 100
                }
                
                # Add reasoning if provided
                if reasoning:
                    log_entry['reasoning'] = reasoning
                else:
                    # Generate basic reasoning from option data
                    log_entry['reasoning'] = {
                        'atm_distance_pct': selected_option.get('strike_distance', 0) * 100,
                        'volume': selected_option.get('volume', 0),
                        'open_interest': selected_option.get('open_interest', 0),
                        'spread_abs': (selected_option.get('ask', 0) - selected_option.get('bid', 0)),
                        'spread_pct': selected_option.get('spread_pct', 0),
                        'spread_acceptable': selected_option.get('spread_pct', 100) < 10,
                        'price_within_max': selected_option.get('price', 0) <= max_price
                    }
            
            # Write to JSONL file (one entry per line)
            with open(self.json_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.debug(f"Logged selection for {ticker}: {selected_option.get('symbol') if selected_option else 'None'}")
            
        except Exception as e:
            logger.error(f"Error logging selection: {e}")

