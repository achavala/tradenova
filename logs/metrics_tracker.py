"""
Metrics Tracker
Tracks P&L, win rate, Sharpe ratio, and other metrics
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MetricsTracker:
    """Track trading metrics"""
    
    def __init__(self, log_dir: str = "./logs"):
        """
        Initialize metrics tracker
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        self.trades: List[Dict] = []
        self.daily_pnl: Dict[str, float] = {}
        self.agent_decisions: List[Dict] = []
        self.rl_predictions: List[Dict] = []
        
    def record_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        qty: float,
        side: str,
        pnl: float,
        agent_name: Optional[str] = None,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None
    ):
        """Record a trade"""
        trade = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'qty': qty,
            'side': side,
            'pnl': pnl,
            'agent_name': agent_name,
            'entry_time': entry_time.isoformat() if entry_time else datetime.now().isoformat(),
            'exit_time': exit_time.isoformat() if exit_time else datetime.now().isoformat()
        }
        
        self.trades.append(trade)
        
        # Update daily P&L
        date = datetime.now().date().isoformat()
        if date not in self.daily_pnl:
            self.daily_pnl[date] = 0.0
        self.daily_pnl[date] += pnl
        
        # Save to file
        self._save_trades()
        
        logger.info(f"Trade recorded: {symbol} P&L=${pnl:.2f}")
    
    def record_agent_decision(
        self,
        symbol: str,
        agent_name: str,
        action: str,
        confidence: float,
        reasoning: str
    ):
        """Record agent decision"""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'agent_name': agent_name,
            'action': action,
            'confidence': confidence,
            'reasoning': reasoning
        }
        
        self.agent_decisions.append(decision)
        self._save_agent_decisions()
    
    def record_rl_prediction(
        self,
        symbol: str,
        action: float,
        confidence: float,
        observation: Optional[np.ndarray] = None
    ):
        """Record RL prediction"""
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': float(action),
            'confidence': confidence
        }
        
        self.rl_predictions.append(prediction)
        self._save_rl_predictions()
    
    def calculate_metrics(self, lookback_days: int = 30) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
        
        # Filter recent trades
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t['entry_time']) >= cutoff_date
        ]
        
        if not recent_trades:
            recent_trades = self.trades
        
        # Calculate metrics
        pnls = [t['pnl'] for t in recent_trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        total_trades = len(recent_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        total_pnl = sum(pnls)
        
        # Sharpe ratio (annualized)
        if len(pnls) > 1:
            returns = np.array(pnls)
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
        else:
            sharpe = 0.0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        # Average win/loss
        avg_win = np.mean(winning_trades) if winning_trades else 0.0
        avg_loss = np.mean(losing_trades) if losing_trades else 0.0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        }
    
    def get_agent_performance(self) -> Dict:
        """Get performance by agent"""
        agent_stats = {}
        
        for trade in self.trades:
            agent = trade.get('agent_name', 'Unknown')
            if agent not in agent_stats:
                agent_stats[agent] = {
                    'trades': 0,
                    'wins': 0,
                    'total_pnl': 0.0
                }
            
            agent_stats[agent]['trades'] += 1
            agent_stats[agent]['total_pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                agent_stats[agent]['wins'] += 1
        
        # Calculate win rates
        for agent in agent_stats:
            stats = agent_stats[agent]
            stats['win_rate'] = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0.0
        
        return agent_stats
    
    def _save_trades(self):
        """Save trades to file"""
        file_path = self.log_dir / "trades.json"
        with open(file_path, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def _save_agent_decisions(self):
        """Save agent decisions to file"""
        file_path = self.log_dir / "agent_decisions.json"
        with open(file_path, 'w') as f:
            json.dump(self.agent_decisions[-1000:], f, indent=2)  # Keep last 1000
    
    def _save_rl_predictions(self):
        """Save RL predictions to file"""
        file_path = self.log_dir / "rl_predictions.json"
        with open(file_path, 'w') as f:
            json.dump(self.rl_predictions[-1000:], f, indent=2)  # Keep last 1000
    
    def generate_daily_report(self) -> str:
        """Generate daily report"""
        metrics = self.calculate_metrics(lookback_days=1)
        agent_perf = self.get_agent_performance()
        
        report = f"""
Daily Trading Report - {datetime.now().date()}
{'='*60}
Total Trades: {metrics['total_trades']}
Win Rate: {metrics['win_rate']:.2%}
Total P&L: ${metrics['total_pnl']:.2f}
Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
Max Drawdown: ${metrics['max_drawdown']:.2f}

Agent Performance:
"""
        for agent, stats in agent_perf.items():
            report += f"  {agent}: {stats['trades']} trades, "
            report += f"{stats['win_rate']:.2%} win rate, "
            report += f"${stats['total_pnl']:.2f} P&L\n"
        
        return report

