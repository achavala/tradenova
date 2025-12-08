"""
Backtest Engine - Per-User Backtesting
Handles backtesting requests for users
"""
import logging
from typing import List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from tradenova_platform.database.models import Backtest
from backtest_trading import BacktestEngine as CoreBacktestEngine

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Manages backtesting for users"""
    
    def __init__(self, database_url: str = "sqlite:///platform.db"):
        """Initialize backtest engine"""
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def run_backtest(
        self,
        user_id: int,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_balance: float = 100000.0
    ) -> Dict:
        """
        Run backtest for user
        
        Args:
            user_id: User ID
            tickers: List of tickers
            start_date: Start date
            end_date: End date
            initial_balance: Initial balance
            
        Returns:
            Backtest results
        """
        try:
            # Create core backtest engine
            engine = CoreBacktestEngine(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
            
            # Run backtest
            engine.run_backtest()
            
            # Get results (from generate_report)
            # We need to extract results from the engine
            # For now, return basic structure
            
            # Save to database
            db = self.SessionLocal()
            try:
                backtest = Backtest(
                    user_id=user_id,
                    name=f"Backtest {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    tickers=tickers,
                    start_date=start_date,
                    end_date=end_date,
                    initial_balance=initial_balance,
                    final_balance=engine.current_balance,
                    total_return_pct=((engine.current_balance - initial_balance) / initial_balance) * 100,
                    total_trades=len(engine.trades),
                    win_rate=len([t for t in engine.trades if t['pnl'] > 0]) / len(engine.trades) * 100 if engine.trades else 0.0,
                    results_json=json.dumps({
                        'trades': engine.trades,
                        'equity_curve': [
                            {
                                'timestamp': p['timestamp'].isoformat() if hasattr(p['timestamp'], 'isoformat') else str(p['timestamp']),
                                'equity': p['equity'],
                                'balance': p['balance'],
                                'positions': p['positions']
                            }
                            for p in engine.equity_curve
                        ]
                    })
                )
                db.add(backtest)
                db.commit()
                
                return {
                    "backtest_id": backtest.id,
                    "user_id": user_id,
                    "tickers": tickers,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "initial_balance": initial_balance,
                    "final_balance": engine.current_balance,
                    "total_return_pct": ((engine.current_balance - initial_balance) / initial_balance) * 100,
                    "total_trades": len(engine.trades),
                    "win_rate": len([t for t in engine.trades if t['pnl'] > 0]) / len(engine.trades) * 100 if engine.trades else 0.0
                }
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving backtest: {e}")
                raise
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise
    
    def get_backtest_history(self, user_id: int) -> List[Dict]:
        """Get backtest history for user"""
        db = self.SessionLocal()
        try:
            backtests = db.query(Backtest).filter(
                Backtest.user_id == user_id
            ).order_by(Backtest.created_at.desc()).limit(50).all()
            
            return [
                {
                    'id': bt.id,
                    'name': bt.name,
                    'tickers': bt.tickers,
                    'start_date': bt.start_date.isoformat(),
                    'end_date': bt.end_date.isoformat(),
                    'initial_balance': bt.initial_balance,
                    'final_balance': bt.final_balance,
                    'total_return_pct': bt.total_return_pct,
                    'total_trades': bt.total_trades,
                    'win_rate': bt.win_rate,
                    'created_at': bt.created_at.isoformat()
                }
                for bt in backtests
            ]
        finally:
            db.close()

