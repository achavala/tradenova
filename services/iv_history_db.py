"""
IV History Database
Stores and retrieves historical IV data for IV Rank and Percentile calculations
"""
import sqlite3
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class IVHistoryDB:
    """
    Database for storing historical IV data
    
    Schema:
    - symbol: Stock symbol
    - date: Date (YYYY-MM-DD)
    - iv: Implied volatility (decimal, e.g., 0.20 for 20%)
    - expiration_date: Option expiration date used
    - strike: Strike price used
    - option_type: 'call' or 'put'
    - created_at: Timestamp when record was created
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize IV history database
        
        Args:
            db_path: Path to SQLite database file (defaults to data/iv_history.db)
        """
        if db_path is None:
            db_path = Path('data/iv_history.db')
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                iv REAL NOT NULL,
                expiration_date DATE,
                strike REAL,
                option_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date, expiration_date, strike, option_type)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON iv_history(symbol, date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol 
            ON iv_history(symbol)
        ''')
        
        conn.commit()
        conn.close()
    
    def store_iv(
        self,
        symbol: str,
        iv: float,
        date: Optional[date] = None,
        expiration_date: Optional[str] = None,
        strike: Optional[float] = None,
        option_type: Optional[str] = None
    ) -> bool:
        """
        Store IV data for a symbol
        
        Args:
            symbol: Stock symbol
            iv: Implied volatility (decimal)
            date: Date (defaults to today)
            expiration_date: Option expiration date
            strike: Strike price
            option_type: 'call' or 'put'
            
        Returns:
            True if stored successfully, False otherwise
        """
        if date is None:
            date = datetime.now().date()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or replace (handle duplicates)
            cursor.execute('''
                INSERT OR REPLACE INTO iv_history 
                (symbol, date, iv, expiration_date, strike, option_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol.upper(), date, iv, expiration_date, strike, option_type))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Error storing IV data for {symbol}: {e}")
            return False
    
    def get_iv_history(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        lookback_days: Optional[int] = None
    ) -> List[float]:
        """
        Get IV history for a symbol
        
        Args:
            symbol: Stock symbol
            start_date: Start date (optional)
            end_date: End date (optional)
            lookback_days: Number of days to look back (optional)
            
        Returns:
            List of IV values (most recent first)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = 'SELECT iv FROM iv_history WHERE symbol = ?'
            params = [symbol.upper()]
            
            if lookback_days:
                cutoff_date = (datetime.now().date() - timedelta(days=lookback_days))
                query += ' AND date >= ?'
                params.append(cutoff_date)
            elif start_date:
                query += ' AND date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY date DESC'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df['iv'].tolist() if not df.empty else []
        except Exception as e:
            logger.error(f"Error retrieving IV history for {symbol}: {e}")
            return []
    
    def get_iv_dataframe(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        lookback_days: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get IV history as DataFrame
        
        Args:
            symbol: Stock symbol
            start_date: Start date (optional)
            end_date: End date (optional)
            lookback_days: Number of days to look back (optional)
            
        Returns:
            DataFrame with columns: date, iv, expiration_date, strike, option_type
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
                SELECT date, iv, expiration_date, strike, option_type 
                FROM iv_history 
                WHERE symbol = ?
            '''
            params = [symbol.upper()]
            
            if lookback_days:
                cutoff_date = (datetime.now().date() - timedelta(days=lookback_days))
                query += ' AND date >= ?'
                params.append(cutoff_date)
            elif start_date:
                query += ' AND date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY date DESC'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            logger.error(f"Error retrieving IV DataFrame for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_iv(self, symbol: str) -> Optional[float]:
        """
        Get latest IV value for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest IV value or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT iv FROM iv_history 
                WHERE symbol = ? 
                ORDER BY date DESC, created_at DESC 
                LIMIT 1
            ''', (symbol.upper(),))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error retrieving latest IV for {symbol}: {e}")
            return None
    
    def get_iv_range(
        self,
        symbol: str,
        lookback_days: int = 365
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Get min and max IV over lookback period
        
        Args:
            symbol: Stock symbol
            lookback_days: Number of days to look back (default: 365 for 52-week)
            
        Returns:
            Tuple of (min_iv, max_iv) or (None, None) if no data
        """
        iv_history = self.get_iv_history(symbol, lookback_days=lookback_days)
        
        if not iv_history:
            return (None, None)
        
        return (min(iv_history), max(iv_history))
    
    def has_data(self, symbol: str, min_days: int = 30) -> bool:
        """
        Check if symbol has sufficient IV history
        
        Args:
            symbol: Stock symbol
            min_days: Minimum number of days required
            
        Returns:
            True if has sufficient data
        """
        iv_history = self.get_iv_history(symbol, lookback_days=min_days)
        return len(iv_history) >= min_days
    
    def get_symbols(self) -> List[str]:
        """
        Get list of symbols with IV data
        
        Returns:
            List of unique symbols
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT DISTINCT symbol FROM iv_history')
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error retrieving symbols: {e}")
            return []
    
    def get_data_summary(self) -> Dict[str, int]:
        """
        Get summary of data in database
        
        Returns:
            Dictionary with symbol -> record count
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, COUNT(*) as count 
                FROM iv_history 
                GROUP BY symbol
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            return {row[0]: row[1] for row in results}
        except Exception as e:
            logger.error(f"Error retrieving data summary: {e}")
            return {}

