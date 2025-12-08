"""
Historical Data Replay Client
Replays real historical market data to simulate live trading for weekend testing
Uses ONLY real historical data from Alpaca - no fake entries
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta, time
import pandas as pd
from alpaca_trade_api.rest import TimeFrame
import time as time_module

from alpaca_client import AlpacaClient
from config import Config

logger = logging.getLogger(__name__)

class HistoricalReplayClient:
    """
    Wraps AlpacaClient to replay historical data as if it's live
    
    Features:
    - Uses REAL historical data from Alpaca
    - Simulates market hours (9:30 AM - 4:00 PM ET)
    - Replays data in real-time or accelerated time
    - Makes system think market is open
    """
    
    def __init__(
        self,
        replay_date: datetime,
        real_alpaca_client: AlpacaClient,
        speed_multiplier: float = 1.0,
        use_intraday: bool = True
    ):
        """
        Initialize historical replay client
        
        Args:
            replay_date: Date to replay (e.g., datetime(2025, 12, 4))
            real_alpaca_client: Real Alpaca client for fetching historical data
            speed_multiplier: Speed multiplier (1.0 = real-time, 10.0 = 10x speed)
            use_intraday: If True, use 5-minute bars for intraday replay
        """
        self.replay_date = replay_date.date()
        self.real_client = real_alpaca_client
        self.speed_multiplier = speed_multiplier
        self.use_intraday = use_intraday
        
        # Market hours (ET)
        self.market_open = time(9, 30)  # 9:30 AM
        self.market_close = time(16, 0)  # 4:00 PM
        
        # Current simulation time (starts at market open, timezone-aware)
        from pytz import UTC
        self.sim_time = UTC.localize(datetime.combine(self.replay_date, self.market_open))
        self.sim_start_time = time_module.time()
        
        # Cache for historical data
        self._historical_cache: Dict[str, pd.DataFrame] = {}
        self._intraday_cache: Dict[str, pd.DataFrame] = {}
        
        # Track positions (simulated)
        self._simulated_positions: Dict[str, Dict] = {}
        
        logger.info(f"📅 Historical Replay initialized for {self.replay_date}")
        logger.info(f"⏱️  Speed multiplier: {speed_multiplier}x")
        logger.info(f"📊 Using {'intraday (5min)' if use_intraday else 'daily'} bars")
    
    def _get_current_sim_time(self) -> datetime:
        """Get current simulation time (timezone-aware)"""
        from pytz import UTC
        
        if self.speed_multiplier == 0:
            # Manual mode - return current sim_time (make timezone-aware)
            if self.sim_time.tzinfo is None:
                return UTC.localize(self.sim_time)
            return self.sim_time
        
        # Calculate elapsed real time
        elapsed_real = time_module.time() - self.sim_start_time
        elapsed_sim = elapsed_real * self.speed_multiplier
        
        # Add to market open time
        current_sim = datetime.combine(self.replay_date, self.market_open) + timedelta(seconds=elapsed_sim)
        
        # Make timezone-aware (ET timezone, but convert to UTC for consistency with Alpaca data)
        if current_sim.tzinfo is None:
            current_sim = UTC.localize(current_sim)
        
        # Don't go past market close
        market_close_dt = UTC.localize(datetime.combine(self.replay_date, self.market_close))
        if current_sim > market_close_dt:
            current_sim = market_close_dt
        
        self.sim_time = current_sim
        return current_sim
    
    def _load_historical_bars(self, symbol: str, timeframe: TimeFrame) -> pd.DataFrame:
        """Load historical bars for the replay date"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self._historical_cache:
            return self._historical_cache[cache_key]
        
        # Fetch real historical data from Alpaca
        start_date = datetime.combine(self.replay_date, time.min) - timedelta(days=60)
        end_date = datetime.combine(self.replay_date, time.max)
        
        logger.info(f"📥 Loading REAL historical data for {symbol} on {self.replay_date}")
        bars = self.real_client.get_historical_bars(
            symbol,
            timeframe,
            start_date,
            end_date
        )
        
        if bars.empty:
            logger.warning(f"⚠️  No historical data found for {symbol} on {self.replay_date}")
            return pd.DataFrame()
        
        # Filter to replay date only (for intraday - 5 minute bars)
        # Check if timeframe is 5-minute by checking if it's not Day/Week/Month
        from alpaca_trade_api.rest import TimeFrameUnit
        if hasattr(timeframe, 'unit') and timeframe.unit == TimeFrameUnit.Minute and not bars.empty:
            bars = bars[bars.index.date == self.replay_date]
        
        self._historical_cache[cache_key] = bars
        logger.info(f"✅ Loaded {len(bars)} bars for {symbol}")
        
        return bars
    
    def get_account(self) -> Dict:
        """Get account information (uses real account)"""
        return self.real_client.get_account()
    
    def get_positions(self) -> List[Dict]:
        """Get positions (combines real and simulated)"""
        real_positions = self.real_client.get_positions()
        
        # Add simulated positions
        for symbol, pos in self._simulated_positions.items():
            real_positions.append(pos)
        
        return real_positions
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for symbol"""
        # Check real positions first
        real_pos = self.real_client.get_position(symbol)
        if real_pos:
            return real_pos
        
        # Check simulated positions
        return self._simulated_positions.get(symbol)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price at current simulation time
        Uses REAL historical data
        """
        current_sim = self._get_current_sim_time()
        
        if self.use_intraday:
            # Use 5-minute bars for intraday prices
            # Create 5-minute timeframe
            from alpaca_trade_api.rest import TimeFrameUnit
            tf_5min = TimeFrame(5, TimeFrameUnit.Minute)
            bars = self._load_historical_bars(symbol, tf_5min)
            
            if bars.empty:
                # Fallback to daily bars
                bars = self._load_historical_bars(symbol, TimeFrame.Day)
                if not bars.empty:
                    # Use close price of the day
                    return float(bars.iloc[-1]['close'])
                return None
            
            # Find the bar at or before current simulation time
            bars_before = bars[bars.index <= current_sim]
            if not bars_before.empty:
                return float(bars_before.iloc[-1]['close'])
            
            # If no bar found yet, use first bar's open
            if not bars.empty:
                return float(bars.iloc[0]['open'])
        else:
            # Use daily bars
            bars = self._load_historical_bars(symbol, TimeFrame.Day)
            if not bars.empty:
                # Use close price of the day
                return float(bars.iloc[-1]['close'])
        
        return None
    
    def get_historical_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Get historical bars up to current simulation time
        Returns REAL historical data, truncated to simulation time
        """
        from pytz import UTC
        
        # Load all historical data
        bars = self._load_historical_bars(symbol, timeframe)
        
        if bars.empty:
            return pd.DataFrame()
        
        # Make start/end timezone-aware if needed
        if start.tzinfo is None:
            start = UTC.localize(start)
        if end.tzinfo is None:
            end = UTC.localize(end)
        
        # Filter to requested date range
        bars = bars[(bars.index >= start) & (bars.index <= end)]
        
        # Truncate to current simulation time
        current_sim = self._get_current_sim_time()
        bars = bars[bars.index <= current_sim]
        
        return bars
    
    def is_market_open(self) -> bool:
        """
        Check if market is open at current simulation time
        Simulates market hours: 9:30 AM - 4:00 PM ET
        """
        current_sim = self._get_current_sim_time()
        current_time = current_sim.time()
        
        # Check if within market hours
        is_open = self.market_open <= current_time < self.market_close
        
        # Also check if it's a weekday (markets closed on weekends)
        weekday = current_sim.weekday()  # 0=Monday, 6=Sunday
        is_weekday = weekday < 5
        
        return is_open and is_weekday
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = 'market',
        time_in_force: str = 'day',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Place order (simulated - logs but doesn't execute)
        In replay mode, we simulate orders but don't actually place them
        """
        current_price = self.get_latest_price(symbol)
        if current_price is None:
            logger.warning(f"⚠️  Cannot place order for {symbol}: no price data")
            return None
        
        current_sim = self._get_current_sim_time()
        
        # Simulate order execution
        order_id = f"SIM_{symbol}_{int(current_sim.timestamp())}"
        
        logger.info(f"📝 SIMULATED ORDER: {side} {qty} {symbol} @ ${current_price:.2f} (sim time: {current_sim.strftime('%H:%M:%S')})")
        
        order_result = {
            'id': order_id,
            'symbol': symbol,
            'qty': float(qty),
            'side': side,
            'type': order_type,
            'status': 'filled',
            'filled_qty': float(qty),
            'filled_avg_price': current_price,
            'simulated': True,
            'sim_time': current_sim.isoformat()
        }
        
        # Track simulated position
        if side == 'buy':
            if symbol in self._simulated_positions:
                pos = self._simulated_positions[symbol]
                pos['qty'] += qty
                pos['avg_entry_price'] = (
                    (pos['avg_entry_price'] * (pos['qty'] - qty) + current_price * qty) / pos['qty']
                )
            else:
                self._simulated_positions[symbol] = {
                    'symbol': symbol,
                    'qty': float(qty),
                    'avg_entry_price': current_price,
                    'current_price': current_price,
                    'side': 'long',
                    'unrealized_pl': 0.0,
                    'unrealized_plpc': 0.0
                }
        elif side == 'sell':
            if symbol in self._simulated_positions:
                pos = self._simulated_positions[symbol]
                pos['qty'] -= qty
                if pos['qty'] <= 0:
                    del self._simulated_positions[symbol]
        
        return order_result
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (simulated)"""
        logger.info(f"📝 SIMULATED CANCEL: Order {order_id}")
        return True
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict]:
        """Get orders (returns empty in simulation)"""
        return []
    
    def get_current_sim_time(self) -> datetime:
        """Get current simulation time"""
        return self._get_current_sim_time()
    
    def advance_time(self, seconds: int):
        """Manually advance simulation time (for speed_multiplier=0)"""
        from pytz import UTC
        self.sim_time += timedelta(seconds=seconds)
        market_close_dt = UTC.localize(datetime.combine(self.replay_date, self.market_close))
        if self.sim_time > market_close_dt:
            self.sim_time = market_close_dt

