"""
Trading Engine - Per-User Trading Execution
Handles live trading for each user with isolated risk management
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradenova_platform.database.models import Portfolio, Position, Trade
from core.live.integrated_trader import IntegratedTrader
from core.risk.advanced_risk_manager import AdvancedRiskManager
from config import Config

logger = logging.getLogger(__name__)

class TradingEngine:
    """Manages trading execution for users"""
    
    def __init__(self, database_url: str = "sqlite:///platform.db"):
        """Initialize trading engine"""
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.active_traders: Dict[int, IntegratedTrader] = {}
    
    def start_trading(self, user_id: int) -> Dict:
        """
        Start automated trading for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Status dictionary
        """
        db = self.SessionLocal()
        try:
            # Check if already trading
            if user_id in self.active_traders:
                return {"status": "already_running", "user_id": user_id}
            
            # Get user portfolio
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                raise ValueError("Portfolio not found")
            
            # Create risk manager for this user
            risk_manager = AdvancedRiskManager(
                initial_balance=portfolio.initial_balance,
                daily_loss_limit_pct=portfolio.daily_loss_limit_pct / 100,
                max_drawdown_pct=portfolio.max_drawdown_limit_pct / 100,
                max_loss_streak=3
            )
            
            # Create integrated trader
            trader = IntegratedTrader(
                rl_model_path=None,  # Can be configured per user
                use_rl=False,  # Can be enabled per user
                dry_run=False,
                paper_trading=True  # Paper trading for safety
            )
            
            # Override risk manager
            trader.risk_manager = risk_manager
            
            # Store trader
            self.active_traders[user_id] = trader
            
            logger.info(f"Started trading for user {user_id}")
            
            return {
                "status": "started",
                "user_id": user_id,
                "initial_balance": portfolio.initial_balance,
                "risk_settings": {
                    "daily_loss_limit_pct": portfolio.daily_loss_limit_pct,
                    "max_drawdown_pct": portfolio.max_drawdown_limit_pct,
                    "max_positions": portfolio.max_positions
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting trading for user {user_id}: {e}")
            raise
        finally:
            db.close()
    
    def stop_trading(self, user_id: int) -> Dict:
        """Stop automated trading for a user"""
        if user_id not in self.active_traders:
            return {"status": "not_running", "user_id": user_id}
        
        # Remove trader
        del self.active_traders[user_id]
        
        logger.info(f"Stopped trading for user {user_id}")
        
        return {"status": "stopped", "user_id": user_id}
    
    def get_trading_status(self, user_id: int) -> Dict:
        """Get trading status for user"""
        is_running = user_id in self.active_traders
        
        return {
            "user_id": user_id,
            "is_running": is_running,
            "status": "active" if is_running else "stopped"
        }
    
    def run_trading_cycle(self, user_id: int):
        """Run one trading cycle for a user"""
        if user_id not in self.active_traders:
            return
        
        trader = self.active_traders[user_id]
        
        try:
            # Run trading cycle
            trader.run_trading_cycle()
            
            # Update portfolio in database
            # This would sync positions and P&L
            # Implementation depends on how IntegratedTrader exposes data
            
        except Exception as e:
            logger.error(f"Error in trading cycle for user {user_id}: {e}")

