"""
Multi-Agent Trading Orchestrator
Coordinates all agents and integrates with TradeNova
"""
import logging
from typing import Dict, List, Optional
import pandas as pd

from core.features.indicators import FeatureEngine
from core.regime.classifier import RegimeClassifier, RegimeSignal
from core.agents import (
    TrendAgent, MeanReversionAgent, FVGAgent, 
    VolatilityAgent, EMAAgent, OptionsAgent,
    ThetaHarvesterAgent, GammaScalperAgent
)
from core.policy_adaptation.meta_policy import MetaPolicyController
from core.agents.base_agent import TradeIntent
from services.options_data_feed import OptionsDataFeed
from services.iv_calculator import IVCalculator
from services.gex_calculator import GEXCalculator

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """Orchestrates multi-agent trading system"""
    
    def __init__(self, alpaca_client):
        """
        Initialize orchestrator
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.feature_engine = FeatureEngine()
        self.regime_classifier = RegimeClassifier()
        self.meta_policy = MetaPolicyController()
        
        # Initialize options services
        self.options_feed = OptionsDataFeed(alpaca_client)
        self.iv_calculator = IVCalculator()
        self.gex_calculator = GEXCalculator()
        
        # Initialize agents
        self.agents = [
            TrendAgent(),
            MeanReversionAgent(),
            FVGAgent(),
            VolatilityAgent(),
            EMAAgent(),  # Works for all tickers in Config.TICKERS
            OptionsAgent(self.options_feed, self.iv_calculator),
            ThetaHarvesterAgent(self.options_feed, self.iv_calculator, self.gex_calculator),
            GammaScalperAgent(self.options_feed, self.iv_calculator, self.gex_calculator)
        ]
        
        logger.info(f"Initialized MultiAgentOrchestrator with {len(self.agents)} agents")
    
    def analyze_symbol(self, symbol: str, bars: pd.DataFrame) -> Optional[TradeIntent]:
        """
        Analyze symbol and generate trade intent
        
        Args:
            symbol: Trading symbol
            bars: DataFrame with OHLCV data
            
        Returns:
            TradeIntent or None
        """
        # Explicitly exclude SPY (user requirement)
        if symbol == "SPY":
            logger.debug(f"{symbol}: SPY excluded from trading")
            return None
        
        # Only analyze symbols in configured ticker list
        from config import Config
        if symbol not in Config.TICKERS:
            logger.debug(f"{symbol}: Not in configured ticker list")
            return None
        
        if bars.empty or len(bars) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            return None
        
        try:
            # Calculate features
            features = self.feature_engine.calculate_all_features(bars)
            if not features:
                return None
            
            # Add current price
            features['current_price'] = bars['close'].iloc[-1]
            
            # Classify regime
            regime_signal = self.regime_classifier.classify(features)
            
            if regime_signal.confidence < 0.30:  # Lowered from 0.4 to allow more trades (target: 2-5/day)
                logger.debug(f"{symbol}: Low regime confidence ({regime_signal.confidence:.2f})")
                return None
            
            # Get intents from all agents
            intents = []
            for agent in self.agents:
                try:
                    intent = agent.evaluate(symbol, regime_signal, features)
                    if intent:
                        intents.append(intent)
                        logger.debug(f"{symbol}: {agent.name} generated {intent.direction.value} signal (confidence: {intent.confidence:.2f})")
                except Exception as e:
                    logger.error(f"Error in {agent.name} for {symbol}: {e}")
            
            if not intents:
                return None
            
            # Meta-policy arbitration
            final_intent = self.meta_policy.arbitrate(
                intents,
                regime_signal.regime_type.value,
                regime_signal.volatility_level.value
            )
            
            if final_intent:
                logger.info(f"{symbol}: Final intent - {final_intent.direction.value} "
                          f"(confidence: {final_intent.confidence:.2f}, "
                          f"agent: {final_intent.agent_name})")
            
            return final_intent
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def update_agent_performance(self, agent_name: str, pnl: float):
        """Update agent performance"""
        for agent in self.agents:
            if agent.name == agent_name:
                agent.update_fitness(pnl)
                # Update meta-policy weight
                self.meta_policy.update_agent_weight(agent_name, agent.get_fitness())
                break
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        status = {}
        for agent in self.agents:
            status[agent.name] = {
                'fitness': agent.get_fitness(),
                'trade_count': agent.trade_count,
                'win_count': agent.win_count,
                'win_rate': agent.win_count / agent.trade_count if agent.trade_count > 0 else 0.0
            }
        return status

