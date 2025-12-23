"""
Option Universe Filter
Filters options BEFORE signal generation to ensure only liquid, tradable contracts
are considered. This is Phase-0 requirement: Option Universe Filter BEFORE signals.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OptionLiquidityMetrics:
    """Liquidity metrics for an option contract"""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    spread_pct: float
    quote_age_seconds: float
    is_liquid: bool
    reason: str

class OptionUniverseFilter:
    """
    Filters option universe to only liquid, tradable contracts.
    
    Phase-0 Rule: This filter MUST run BEFORE signal generation.
    Only options passing this filter should be considered by RL/agents.
    """
    
    def __init__(
        self,
        max_spread_pct: float = 20.0,
        min_bid: float = 0.01,
        min_bid_size: int = 1,
        max_quote_age_seconds: float = 5.0,
        min_volume: int = 0  # Optional: can require minimum volume
    ):
        """
        Initialize option universe filter
        
        Args:
            max_spread_pct: Maximum bid-ask spread percentage (default: 20%)
            min_bid: Minimum bid price (default: $0.01)
            min_bid_size: Minimum bid size in contracts (default: 1)
            max_quote_age_seconds: Maximum quote age in seconds (default: 5)
            min_volume: Minimum daily volume (default: 0, optional)
        """
        self.max_spread_pct = max_spread_pct
        self.min_bid = min_bid
        self.min_bid_size = min_bid_size
        self.max_quote_age_seconds = max_quote_age_seconds
        self.min_volume = min_volume
        
        logger.info(f"OptionUniverseFilter initialized:")
        logger.info(f"  Max spread: {max_spread_pct}%")
        logger.info(f"  Min bid: ${min_bid:.2f}")
        logger.info(f"  Min bid size: {min_bid_size} contracts")
        logger.info(f"  Max quote age: {max_quote_age_seconds}s")
    
    def filter_options_chain(
        self,
        options_chain: List[Dict],
        current_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Filter options chain to only liquid, tradable contracts
        
        Args:
            options_chain: List of option contracts from API
            current_time: Current time for quote age calculation (default: now)
            
        Returns:
            Filtered list of liquid options
        """
        if current_time is None:
            current_time = datetime.now()
        
        liquid_options = []
        filtered_count = 0
        
        for contract in options_chain:
            metrics = self._calculate_liquidity_metrics(contract, current_time)
            
            if metrics.is_liquid:
                liquid_options.append(contract)
            else:
                filtered_count += 1
                logger.debug(f"Filtered {contract.get('symbol', 'unknown')}: {metrics.reason}")
        
        logger.info(f"Option universe filter: {len(liquid_options)}/{len(options_chain)} options passed liquidity check")
        
        return liquid_options
    
    def _calculate_liquidity_metrics(
        self,
        contract: Dict,
        current_time: datetime
    ) -> OptionLiquidityMetrics:
        """
        Calculate liquidity metrics for a single option contract
        
        Args:
            contract: Option contract dictionary
            current_time: Current time for quote age
            
        Returns:
            OptionLiquidityMetrics object
        """
        symbol = contract.get('symbol') or contract.get('contract_symbol') or 'unknown'
        
        # Extract bid/ask from various possible locations
        bid = self._extract_price(contract, 'bid', 'bid_price', 'last_bid')
        ask = self._extract_price(contract, 'ask', 'ask_price', 'last_ask')
        mid = self._extract_price(contract, 'mid', 'mid_price', 'last_price')
        
        # If no bid/ask, try to construct from mid
        if bid is None and ask is None and mid is not None:
            # Assume 5% spread around mid (conservative)
            bid = mid * 0.975
            ask = mid * 1.025
        
        # Extract sizes
        bid_size = contract.get('bid_size', contract.get('bid_qty', 0))
        ask_size = contract.get('ask_size', contract.get('ask_qty', 0))
        
        # Extract quote timestamp
        quote_time = self._extract_timestamp(contract)
        quote_age = (current_time - quote_time).total_seconds() if quote_time else float('inf')
        
        # Calculate spread percentage
        if bid and ask and bid > 0:
            spread_pct = ((ask - bid) / bid) * 100
        elif mid and mid > 0:
            # Estimate spread from mid (conservative)
            spread_pct = 5.0  # Assume 5% if we only have mid
        else:
            spread_pct = float('inf')
        
        # Check liquidity criteria
        is_liquid = True
        reasons = []
        
        if bid is None or bid < self.min_bid:
            is_liquid = False
            reasons.append(f"Bid too low or missing (${bid:.4f} < ${self.min_bid:.2f})")
        
        if spread_pct > self.max_spread_pct:
            is_liquid = False
            reasons.append(f"Spread too wide ({spread_pct:.2f}% > {self.max_spread_pct}%)")
        
        if bid_size < self.min_bid_size:
            is_liquid = False
            reasons.append(f"Bid size too small ({bid_size} < {self.min_bid_size})")
        
        if quote_age > self.max_quote_age_seconds:
            is_liquid = False
            reasons.append(f"Quote stale ({quote_age:.1f}s > {self.max_quote_age_seconds}s)")
        
        # Optional: volume check
        if self.min_volume > 0:
            volume = contract.get('volume', contract.get('daily_volume', 0))
            if volume < self.min_volume:
                is_liquid = False
                reasons.append(f"Volume too low ({volume} < {self.min_volume})")
        
        reason = "; ".join(reasons) if reasons else "Liquid"
        
        return OptionLiquidityMetrics(
            symbol=symbol,
            bid=bid or 0.0,
            ask=ask or 0.0,
            bid_size=int(bid_size) if bid_size else 0,
            ask_size=int(ask_size) if ask_size else 0,
            spread_pct=spread_pct,
            quote_age_seconds=quote_age,
            is_liquid=is_liquid,
            reason=reason
        )
    
    def _extract_price(self, contract: Dict, *keys: str) -> Optional[float]:
        """Extract price from contract using multiple possible keys"""
        for key in keys:
            value = contract.get(key)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        
        # Try nested structures
        if 'quote' in contract:
            for key in keys:
                value = contract['quote'].get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        
        if 'day' in contract:
            for key in keys:
                value = contract['day'].get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _extract_timestamp(self, contract: Dict) -> Optional[datetime]:
        """Extract quote timestamp from contract"""
        # Try various timestamp fields
        timestamp_fields = ['quote_time', 'last_quote_time', 'updated_at', 'timestamp']
        
        for field in timestamp_fields:
            value = contract.get(field)
            if value:
                try:
                    if isinstance(value, str):
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    elif isinstance(value, (int, float)):
                        return datetime.fromtimestamp(value)
                except (ValueError, TypeError):
                    continue
        
        # If no timestamp, assume stale
        return None
    
    def is_option_tradable(
        self,
        contract: Dict,
        current_time: Optional[datetime] = None
    ) -> tuple[bool, str]:
        """
        Quick check if a single option is tradable
        
        Args:
            contract: Option contract dictionary
            current_time: Current time (default: now)
            
        Returns:
            (is_tradable, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        metrics = self._calculate_liquidity_metrics(contract, current_time)
        return metrics.is_liquid, metrics.reason

