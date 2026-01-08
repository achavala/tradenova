"""
Ticker Configuration & Stratification
Implements Architect 3 & 4 recommendations for per-symbol risk profiles
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TickerTier(Enum):
    """Ticker liquidity tiers"""
    TIER_A = "A"  # TRUE 0-14 DTE (Swing + Selective 0DTE)
    TIER_B = "B"  # 7-30 DTE ONLY (NO 0DTE)
    TIER_C = "C"  # NO 0DTE OPTIONS - Stock or 30+ DTE only


class TradingMode(Enum):
    """Trading playbook modes"""
    SCALP = "scalp"   # 0-3 DTE
    SWING = "swing"   # 7-21 DTE


@dataclass
class TickerConfig:
    """Per-symbol configuration"""
    symbol: str
    tier: TickerTier
    
    # Liquidity requirements
    min_option_volume: int = 100
    min_open_interest: int = 500
    max_spread_pct: float = 0.05  # 5% max spread
    
    # Position sizing
    max_position_pct: float = 0.10  # 10% of portfolio
    
    # DTE constraints
    min_dte: int = 0
    max_dte: int = 14
    scalp_allowed: bool = True
    
    # Special flags
    high_gamma_risk: bool = False
    earnings_sensitive: bool = True
    
    def allows_dte(self, dte: int) -> Tuple[bool, str]:
        """Check if DTE is allowed for this ticker"""
        if dte < self.min_dte:
            return False, f"{self.symbol}: DTE {dte} below minimum {self.min_dte}"
        if dte > self.max_dte:
            return False, f"{self.symbol}: DTE {dte} above maximum {self.max_dte}"
        if dte <= 3 and not self.scalp_allowed:
            return False, f"{self.symbol}: 0DTE/Scalp not allowed (Tier {self.tier.value})"
        return True, ""
    
    def get_mode(self, dte: int) -> TradingMode:
        """Determine trading mode based on DTE"""
        if dte <= 3 and self.scalp_allowed:
            return TradingMode.SCALP
        return TradingMode.SWING


# ============================================================================
# TICKER TIER DEFINITIONS (Architect 4's Final Tiering)
# ============================================================================

TIER_A_TICKERS: Dict[str, TickerConfig] = {
    # TRUE 0-14 DTE (Swing + Selective 0DTE)
    # Deep OPRA liquidity, Tight spreads, Reliable dealer flow
    
    "NVDA": TickerConfig(
        symbol="NVDA",
        tier=TickerTier.TIER_A,
        min_option_volume=500,
        min_open_interest=2000,
        max_spread_pct=0.03,  # 3% - very liquid
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
        high_gamma_risk=True,  # Volatile stock
    ),
    
    "AAPL": TickerConfig(
        symbol="AAPL",
        tier=TickerTier.TIER_A,
        min_option_volume=500,
        min_open_interest=2000,
        max_spread_pct=0.02,  # 2% - most liquid
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "TSLA": TickerConfig(
        symbol="TSLA",
        tier=TickerTier.TIER_A,
        min_option_volume=500,
        min_open_interest=2000,
        max_spread_pct=0.03,
        max_position_pct=0.08,  # Slightly lower due to volatility
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
        high_gamma_risk=True,
    ),
    
    "MSFT": TickerConfig(
        symbol="MSFT",
        tier=TickerTier.TIER_A,
        min_option_volume=300,
        min_open_interest=1500,
        max_spread_pct=0.02,
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "META": TickerConfig(
        symbol="META",
        tier=TickerTier.TIER_A,
        min_option_volume=300,
        min_open_interest=1500,
        max_spread_pct=0.03,
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "AMZN": TickerConfig(
        symbol="AMZN",
        tier=TickerTier.TIER_A,
        min_option_volume=300,
        min_open_interest=1500,
        max_spread_pct=0.03,
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "GOOG": TickerConfig(
        symbol="GOOG",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=1000,
        max_spread_pct=0.03,
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "AMD": TickerConfig(
        symbol="AMD",
        tier=TickerTier.TIER_A,
        min_option_volume=300,
        min_open_interest=1500,
        max_spread_pct=0.03,
        max_position_pct=0.10,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
        high_gamma_risk=True,
    ),
    
    "AVGO": TickerConfig(
        symbol="AVGO",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=1000,
        max_spread_pct=0.04,
        max_position_pct=0.08,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "MU": TickerConfig(
        symbol="MU",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=1000,
        max_spread_pct=0.04,
        max_position_pct=0.08,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
    
    "SMCI": TickerConfig(
        symbol="SMCI",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=800,
        max_spread_pct=0.05,
        max_position_pct=0.06,  # Lower due to volatility
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
        high_gamma_risk=True,
    ),
    
    "COIN": TickerConfig(
        symbol="COIN",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=800,
        max_spread_pct=0.05,
        max_position_pct=0.06,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
        high_gamma_risk=True,
    ),
    
    "INTC": TickerConfig(
        symbol="INTC",
        tier=TickerTier.TIER_A,
        min_option_volume=200,
        min_open_interest=1000,
        max_spread_pct=0.04,
        max_position_pct=0.08,
        min_dte=0,
        max_dte=14,
        scalp_allowed=True,
    ),
}

TIER_B_TICKERS: Dict[str, TickerConfig] = {
    # 7-30 DTE ONLY (NO 0DTE)
    # High volatility, Wider spreads, Swing options only
    
    "MSTR": TickerConfig(
        symbol="MSTR",
        tier=TickerTier.TIER_B,
        min_option_volume=100,
        min_open_interest=500,
        max_spread_pct=0.08,  # Wider spreads acceptable
        max_position_pct=0.05,  # Lower position size
        min_dte=7,  # NO 0DTE
        max_dte=30,
        scalp_allowed=False,  # NO SCALP
        high_gamma_risk=True,
    ),
    
    "PLTR": TickerConfig(
        symbol="PLTR",
        tier=TickerTier.TIER_B,
        min_option_volume=200,
        min_open_interest=800,
        max_spread_pct=0.06,
        max_position_pct=0.06,
        min_dte=7,
        max_dte=30,
        scalp_allowed=False,
    ),
    
    "HOOD": TickerConfig(
        symbol="HOOD",
        tier=TickerTier.TIER_B,
        min_option_volume=100,
        min_open_interest=500,
        max_spread_pct=0.07,
        max_position_pct=0.05,
        min_dte=7,
        max_dte=30,
        scalp_allowed=False,
    ),
}

TIER_C_TICKERS: Dict[str, TickerConfig] = {
    # NO 0DTE OPTIONS
    # Thin chains, Low OI, Exit risk > alpha
    # These should be stocks or 30+ DTE only
    
    "NBIS": TickerConfig(
        symbol="NBIS",
        tier=TickerTier.TIER_C,
        min_option_volume=50,
        min_open_interest=200,
        max_spread_pct=0.10,
        max_position_pct=0.03,  # Very small positions
        min_dte=14,  # Long DTE only
        max_dte=45,
        scalp_allowed=False,
    ),
    
    "OKLO": TickerConfig(
        symbol="OKLO",
        tier=TickerTier.TIER_C,
        min_option_volume=50,
        min_open_interest=200,
        max_spread_pct=0.10,
        max_position_pct=0.03,
        min_dte=14,
        max_dte=45,
        scalp_allowed=False,
    ),
    
    "IREN": TickerConfig(
        symbol="IREN",
        tier=TickerTier.TIER_C,
        min_option_volume=50,
        min_open_interest=200,
        max_spread_pct=0.10,
        max_position_pct=0.03,
        min_dte=14,
        max_dte=45,
        scalp_allowed=False,
    ),
    
    "RKLB": TickerConfig(
        symbol="RKLB",
        tier=TickerTier.TIER_C,
        min_option_volume=50,
        min_open_interest=200,
        max_spread_pct=0.10,
        max_position_pct=0.03,
        min_dte=14,
        max_dte=45,
        scalp_allowed=False,
    ),
    
    "PATH": TickerConfig(
        symbol="PATH",
        tier=TickerTier.TIER_C,
        min_option_volume=50,
        min_open_interest=200,
        max_spread_pct=0.10,
        max_position_pct=0.03,
        min_dte=14,
        max_dte=45,
        scalp_allowed=False,
    ),
}

# Combined ticker configs
ALL_TICKER_CONFIGS: Dict[str, TickerConfig] = {
    **TIER_A_TICKERS,
    **TIER_B_TICKERS,
    **TIER_C_TICKERS,
}


class TickerConfigManager:
    """Manager for ticker configurations"""
    
    def __init__(self):
        self.configs = ALL_TICKER_CONFIGS
        logger.info(f"TickerConfigManager initialized with {len(self.configs)} tickers")
        logger.info(f"  Tier A: {len(TIER_A_TICKERS)} (0-14 DTE + Scalp)")
        logger.info(f"  Tier B: {len(TIER_B_TICKERS)} (7-30 DTE only)")
        logger.info(f"  Tier C: {len(TIER_C_TICKERS)} (14+ DTE only)")
    
    def get_config(self, symbol: str) -> Optional[TickerConfig]:
        """Get configuration for a symbol"""
        return self.configs.get(symbol)
    
    def get_tier(self, symbol: str) -> Optional[TickerTier]:
        """Get tier for a symbol"""
        config = self.get_config(symbol)
        return config.tier if config else None
    
    def is_scalp_allowed(self, symbol: str) -> bool:
        """Check if scalp trading is allowed for symbol"""
        config = self.get_config(symbol)
        return config.scalp_allowed if config else False
    
    def get_dte_range(self, symbol: str) -> Tuple[int, int]:
        """Get allowed DTE range for symbol"""
        config = self.get_config(symbol)
        if config:
            return config.min_dte, config.max_dte
        return 0, 14  # Default
    
    def check_liquidity(
        self, 
        symbol: str, 
        bid: float, 
        ask: float, 
        volume: int, 
        open_interest: int
    ) -> Tuple[bool, str]:
        """
        Check if option meets liquidity requirements for this ticker
        
        Returns:
            (passes, reason)
        """
        config = self.get_config(symbol)
        if not config:
            return False, f"Unknown ticker: {symbol}"
        
        # Spread check (CRITICAL - Architect 4)
        if ask > 0:
            spread_pct = (ask - bid) / ask
            if spread_pct > config.max_spread_pct:
                return False, f"SPREAD REJECT: {spread_pct:.1%} > {config.max_spread_pct:.1%} max"
        
        # Volume check
        if volume < config.min_option_volume:
            return False, f"VOLUME REJECT: {volume} < {config.min_option_volume} min"
        
        # Open Interest check
        if open_interest < config.min_open_interest:
            return False, f"OI REJECT: {open_interest} < {config.min_open_interest} min"
        
        # Volume/OI ratio check (Architect 4 recommendation)
        if open_interest > 0:
            vol_oi_ratio = volume / open_interest
            if vol_oi_ratio < 0.01:
                return False, f"VOL/OI REJECT: {vol_oi_ratio:.3f} < 0.01 (dead contract)"
        
        return True, "Liquidity OK"
    
    def get_position_size_cap(self, symbol: str) -> float:
        """Get max position size % for symbol"""
        config = self.get_config(symbol)
        return config.max_position_pct if config else 0.10
    
    def validate_trade(
        self,
        symbol: str,
        dte: int,
        bid: float,
        ask: float,
        volume: int,
        open_interest: int,
        gamma: Optional[float] = None
    ) -> Tuple[bool, List[str]]:
        """
        Full trade validation against ticker config
        
        Returns:
            (allowed, list_of_reasons)
        """
        reasons = []
        config = self.get_config(symbol)
        
        if not config:
            return False, [f"Unknown ticker: {symbol}"]
        
        # 1. DTE check
        dte_allowed, dte_reason = config.allows_dte(dte)
        if not dte_allowed:
            reasons.append(f"❌ {dte_reason}")
            return False, reasons
        
        # 2. Liquidity check
        liq_ok, liq_reason = self.check_liquidity(symbol, bid, ask, volume, open_interest)
        if not liq_ok:
            reasons.append(f"❌ {liq_reason}")
            return False, reasons
        
        # 3. Gamma check (if high gamma risk)
        if config.high_gamma_risk and gamma is not None:
            if gamma > 0.50:
                reasons.append(f"⚠️ HIGH GAMMA: {gamma:.2f} - reducing size by 50%")
        
        # 4. Trading mode
        mode = config.get_mode(dte)
        reasons.append(f"✅ Mode: {mode.value.upper()} | Tier: {config.tier.value}")
        
        return True, reasons


# Singleton instance
ticker_config_manager = TickerConfigManager()

