"""
Base Agent Class
All trading agents inherit from this class
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from core.regime.classifier import RegimeSignal, RegimeType

logger = logging.getLogger(__name__)

class TradeDirection(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

@dataclass
class TradeIntent:
    """Trading intent from an agent"""
    direction: TradeDirection
    confidence: float  # 0.0 - 1.0
    position_size_suggestion: float  # Suggested position size
    reasoning: str
    agent_name: str
    symbol: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class BaseAgent(ABC):
    """Base class for all trading agents"""
    
    def __init__(self, name: str, min_confidence: float = 0.6):
        """
        Initialize agent
        
        Args:
            name: Agent name
            min_confidence: Minimum confidence threshold to activate
        """
        self.name = name
        self.min_confidence = min_confidence
        self.fitness_score = 1.0  # Adaptive weight
        self.trade_count = 0
        self.win_count = 0
    
    @abstractmethod
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """
        Check if agent should activate based on regime
        
        Args:
            regime_signal: Current regime classification
            features: Feature dictionary
            
        Returns:
            True if agent should activate
        """
        pass
    
    @abstractmethod
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """
        Evaluate and generate trade intent
        
        Args:
            symbol: Trading symbol
            regime_signal: Current regime classification
            features: Feature dictionary
            
        Returns:
            TradeIntent or None if no signal
        """
        pass
    
    def update_fitness(self, pnl: float):
        """
        Update agent fitness based on trade performance
        
        Args:
            pnl: Profit and loss from trade
        """
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1
        
        # Update fitness (simple win rate based)
        if self.trade_count > 0:
            win_rate = self.win_count / self.trade_count
            self.fitness_score = win_rate
    
    def get_fitness(self) -> float:
        """Get current fitness score"""
        return self.fitness_score

