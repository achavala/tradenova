"""
UVaR (Ultra-Short-Horizon VaR) Calculator - Step 3
Detects tail risk that Greeks alone cannot see.

For 0-30DTE options trading:
- Horizon: 1-3 trading days
- Confidence: 99%
- Method: Historical Simulation (simple, effective)

UVaR is a secondary alarm alongside Greeks caps, not a replacement.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UVaRResult:
    """UVaR calculation result"""
    uvar_1d: float  # 1-day UVaR
    uvar_3d: float  # 3-day UVaR
    uvar_5d: float  # 5-day UVaR (optional)
    confidence: float  # Confidence level (e.g., 0.99)
    current_exposure: float  # Current portfolio value at risk
    status: str  # 'within_limits', 'warning', 'danger'
    percentile_loss: float  # Actual percentile loss
    sample_size: int  # Number of historical observations
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'uvar_1d': round(self.uvar_1d, 2),
            'uvar_3d': round(self.uvar_3d, 2),
            'uvar_5d': round(self.uvar_5d, 2) if hasattr(self, 'uvar_5d') else None,
            'confidence': self.confidence,
            'current_exposure': round(self.current_exposure, 2),
            'status': self.status,
            'percentile_loss': round(self.percentile_loss, 2),
            'sample_size': self.sample_size
        }


class UVaRCalculator:
    """
    UVaR Calculator using Historical Simulation
    
    Simple, effective method for 0-30DTE options:
    - Uses historical portfolio P&L
    - Computes percentile loss
    - No complex modeling needed
    """
    
    def __init__(
        self,
        confidence: float = 0.99,
        lookback_days: int = 90,
        max_uvar_1d: float = -1500.0,
        max_uvar_3d: float = -3000.0
    ):
        """
        Initialize UVaR calculator
        
        Args:
            confidence: Confidence level (default 0.99 = 99%)
            lookback_days: Number of days to look back (default 90)
            max_uvar_1d: Maximum allowed 1-day UVaR (default -$1500)
            max_uvar_3d: Maximum allowed 3-day UVaR (default -$3000)
        """
        self.confidence = confidence
        self.lookback_days = lookback_days
        self.max_uvar_1d = max_uvar_1d
        self.max_uvar_3d = max_uvar_3d
        
        # P&L history storage
        self.pnl_history: List[float] = []
        self.pnl_dates: List[datetime] = []
        
        logger.info(f"UVaR Calculator initialized: confidence={confidence}, lookback={lookback_days} days")
    
    def add_daily_pnl(self, pnl: float, date: Optional[datetime] = None):
        """
        Add daily portfolio P&L to history
        
        Args:
            pnl: Daily portfolio P&L (can be negative)
            date: Date of P&L (default: today)
        """
        if date is None:
            date = datetime.now()
        
        self.pnl_history.append(pnl)
        self.pnl_dates.append(date)
        
        # Keep only recent history
        cutoff_date = date - timedelta(days=self.lookback_days)
        while self.pnl_dates and self.pnl_dates[0] < cutoff_date:
            self.pnl_history.pop(0)
            self.pnl_dates.pop(0)
        
        logger.debug(f"Added P&L: ${pnl:.2f} on {date.strftime('%Y-%m-%d')}")
    
    def calculate_uvar(
        self,
        horizon_days: int = 1,
        current_portfolio_value: Optional[float] = None
    ) -> UVaRResult:
        """
        Calculate UVaR for given horizon
        
        Args:
            horizon_days: Horizon in days (1, 3, or 5)
            current_portfolio_value: Current portfolio value (for exposure calculation)
        
        Returns:
            UVaRResult object
        """
        if len(self.pnl_history) < 30:
            # Not enough data, return conservative estimate
            logger.warning(f"Insufficient P&L history ({len(self.pnl_history)} days). Need at least 30 days.")
            return UVaRResult(
                uvar_1d=-2000.0,  # Conservative default
                uvar_3d=-4000.0,
                uvar_5d=-6000.0,
                confidence=self.confidence,
                current_exposure=current_portfolio_value or 0.0,
                status='warning',
                percentile_loss=-2000.0,
                sample_size=len(self.pnl_history)
            )
        
        # Convert to numpy array for percentile calculation
        pnl_array = np.array(self.pnl_history)
        
        # Calculate percentile loss (1% worst case = 99% confidence)
        percentile = (1 - self.confidence) * 100  # 1% for 99% confidence
        percentile_loss = np.percentile(pnl_array, percentile)
        
        # For multi-day horizons, scale by sqrt(days) (simple approximation)
        # More sophisticated: use rolling multi-day returns
        uvar_1d = percentile_loss
        uvar_3d = percentile_loss * np.sqrt(3)
        uvar_5d = percentile_loss * np.sqrt(5)
        
        # Determine status
        status = self._determine_status(uvar_1d, uvar_3d)
        
        # Current exposure (use portfolio value if provided)
        current_exposure = current_portfolio_value or abs(uvar_1d)
        
        result = UVaRResult(
            uvar_1d=float(uvar_1d),
            uvar_3d=float(uvar_3d),
            uvar_5d=float(uvar_5d),
            confidence=self.confidence,
            current_exposure=current_exposure,
            status=status,
            percentile_loss=float(percentile_loss),
            sample_size=len(self.pnl_history)
        )
        
        logger.debug(f"UVaR calculated: 1d=${uvar_1d:.2f}, 3d=${uvar_3d:.2f}, status={status}")
        
        return result
    
    def check_uvar_limit(
        self,
        current_portfolio_value: Optional[float] = None,
        horizon_days: int = 1
    ) -> Tuple[bool, str, UVaRResult]:
        """
        Check if UVaR is within limits
        
        Args:
            current_portfolio_value: Current portfolio value
            horizon_days: Horizon to check (1 or 3)
        
        Returns:
            Tuple of (within_limits, reason, UVaRResult)
        """
        result = self.calculate_uvar(
            horizon_days=horizon_days,
            current_portfolio_value=current_portfolio_value
        )
        
        if horizon_days == 1:
            limit = self.max_uvar_1d
            uvar_value = result.uvar_1d
        else:
            limit = self.max_uvar_3d
            uvar_value = result.uvar_3d
        
        if uvar_value < limit:
            return (
                False,
                f"UVaR({horizon_days}d) ${uvar_value:.2f} exceeds limit ${limit:.2f}",
                result
            )
        
        return (True, "UVaR within limits", result)
    
    def _determine_status(self, uvar_1d: float, uvar_3d: float) -> str:
        """Determine risk status based on UVaR"""
        # Check if within limits
        if uvar_1d >= self.max_uvar_1d and uvar_3d >= self.max_uvar_3d:
            return 'within_limits'
        
        # Check if extreme (2x limit)
        if uvar_1d < self.max_uvar_1d * 2 or uvar_3d < self.max_uvar_3d * 2:
            return 'danger'
        
        # Warning level
        return 'warning'
    
    def get_pnl_statistics(self) -> Dict:
        """Get P&L statistics for analysis"""
        if not self.pnl_history:
            return {
                'count': 0,
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'percentile_1': 0.0,
                'percentile_99': 0.0
            }
        
        pnl_array = np.array(self.pnl_history)
        
        return {
            'count': len(self.pnl_history),
            'mean': float(np.mean(pnl_array)),
            'std': float(np.std(pnl_array)),
            'min': float(np.min(pnl_array)),
            'max': float(np.max(pnl_array)),
            'percentile_1': float(np.percentile(pnl_array, 1)),
            'percentile_99': float(np.percentile(pnl_array, 99))
        }
    
    def load_pnl_from_file(self, file_path: Path):
        """Load P&L history from file (for persistence)"""
        try:
            if file_path.exists():
                df = pd.read_csv(file_path)
                if 'date' in df.columns and 'pnl' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    for _, row in df.iterrows():
                        self.add_daily_pnl(row['pnl'], row['date'])
                    logger.info(f"Loaded {len(df)} P&L records from {file_path}")
        except Exception as e:
            logger.error(f"Error loading P&L from file: {e}")
    
    def save_pnl_to_file(self, file_path: Path):
        """Save P&L history to file (for persistence)"""
        try:
            df = pd.DataFrame({
                'date': self.pnl_dates,
                'pnl': self.pnl_history
            })
            df.to_csv(file_path, index=False)
            logger.debug(f"Saved {len(df)} P&L records to {file_path}")
        except Exception as e:
            logger.error(f"Error saving P&L to file: {e}")


# Convenience function
def calculate_uvar(
    pnl_history: List[float],
    confidence: float = 0.99,
    horizon_days: int = 1
) -> float:
    """
    Convenience function to calculate UVaR from P&L history
    
    Args:
        pnl_history: List of daily P&L values
        confidence: Confidence level (default 0.99)
        horizon_days: Horizon in days (default 1)
    
    Returns:
        UVaR value (negative number)
    """
    if len(pnl_history) < 30:
        return -2000.0  # Conservative default
    
    pnl_array = np.array(pnl_history)
    percentile = (1 - confidence) * 100
    percentile_loss = np.percentile(pnl_array, percentile)
    
    # Scale by sqrt(days) for multi-day
    return float(percentile_loss * np.sqrt(horizon_days))

