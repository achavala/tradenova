"""
Portfolio Management System
Handles per-user portfolio tracking, positions, and performance
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradenova_platform.database.models import Portfolio, Position, Trade, PerformanceMetrics

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Manages user portfolios"""
    
    def __init__(self, database_url: str = "sqlite:///platform.db"):
        """Initialize portfolio manager"""
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_open_positions(self, user_id: int) -> List[Dict]:
        """Get all open positions for user"""
        db = self.SessionLocal()
        try:
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                return []
            
            positions = []
            for pos in portfolio.positions:
                positions.append({
                    'id': pos.id,
                    'symbol': pos.symbol,
                    'qty': pos.qty,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'side': pos.side,
                    'entry_time': pos.entry_time.isoformat(),
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                    'agent_name': pos.agent_name
                })
            
            return positions
        finally:
            db.close()
    
    def get_trade_history(self, user_id: int, limit: int = 100) -> List[Dict]:
        """Get trade history for user"""
        db = self.SessionLocal()
        try:
            trades = db.query(Trade).filter(
                Trade.user_id == user_id
            ).order_by(Trade.exit_time.desc()).limit(limit).all()
            
            return [
                {
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'qty': trade.qty,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'side': trade.side,
                    'entry_time': trade.entry_time.isoformat(),
                    'exit_time': trade.exit_time.isoformat(),
                    'pnl': trade.pnl,
                    'pnl_pct': trade.pnl_pct,
                    'reason': trade.reason,
                    'agent_name': trade.agent_name
                }
                for trade in trades
            ]
        finally:
            db.close()
    
    def get_performance_metrics(self, user_id: int) -> Dict:
        """Get performance metrics for user"""
        db = self.SessionLocal()
        try:
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                return {}
            
            # Get recent trades for calculations
            trades = db.query(Trade).filter(
                Trade.user_id == user_id
            ).all()
            
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl <= 0]
            
            win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0.0
            avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
            avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
            
            return {
                'initial_balance': portfolio.initial_balance,
                'current_balance': portfolio.current_balance,
                'equity': portfolio.equity,
                'cash': portfolio.cash,
                'total_pnl': portfolio.total_pnl,
                'total_return_pct': portfolio.total_return_pct,
                'max_drawdown_pct': portfolio.max_drawdown_pct,
                'win_rate': win_rate,
                'sharpe_ratio': portfolio.sharpe_ratio,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'average_win': avg_win,
                'average_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
            }
        finally:
            db.close()
    
    def update_portfolio_equity(self, user_id: int, equity: float, cash: float):
        """Update portfolio equity and cash"""
        db = self.SessionLocal()
        try:
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                return
            
            portfolio.equity = equity
            portfolio.cash = cash
            portfolio.current_balance = cash
            portfolio.total_pnl = equity - portfolio.initial_balance
            portfolio.total_return_pct = ((equity - portfolio.initial_balance) / portfolio.initial_balance) * 100
            portfolio.last_updated = datetime.utcnow()
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating portfolio: {e}")
        finally:
            db.close()

