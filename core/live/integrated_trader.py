"""
Integrated Trader
Combines RL predictions, multi-agent system, execution, and risk management
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

from alpaca_client import AlpacaClient
from config import Config
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.broker_executor import BrokerExecutor
from core.risk.advanced_risk_manager import AdvancedRiskManager
from core.risk.profit_manager import ProfitManager
from core.agents.base_agent import TradeIntent, TradeDirection
from alpaca_trade_api.rest import TimeFrame
from rl.predict import RLPredictor
from logs.metrics_tracker import MetricsTracker
from core.live.model_degrade_detector import ModelDegradeDetector
from core.live.ensemble_predictor import EnsemblePredictor
from core.live.news_filter import NewsFilter
import os

logger = logging.getLogger(__name__)

class IntegratedTrader:
    """Integrated trading system combining all components"""
    
    def __init__(
        self,
        rl_model_path: Optional[str] = None,
        use_rl: bool = True,
        dry_run: bool = False,
        paper_trading: bool = False
    ):
        """
        Initialize integrated trader
        
        Args:
            rl_model_path: Path to trained RL model
            use_rl: Whether to use RL predictions
            dry_run: If True, simulate trading without executing orders
            paper_trading: If True, use paper trading account
        """
        self.dry_run = dry_run
        self.paper_trading = paper_trading
        # Initialize clients
        base_url = Config.ALPACA_BASE_URL
        if paper_trading:
            base_url = "https://paper-api.alpaca.markets"
            logger.info("Using PAPER trading account")
        
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            base_url
        )
        
        if dry_run:
            logger.warning("DRY RUN MODE: No orders will be executed")
        
        # Initialize components
        self.orchestrator = MultiAgentOrchestrator(self.client)
        self.executor = BrokerExecutor(self.client)
        
        # Initialize risk manager with ACTUAL account balance (not config default)
        try:
            account = self.client.get_account()
            actual_balance = float(account['equity'])
            logger.info(f"Initializing risk manager with actual balance: ${actual_balance:,.2f}")
        except Exception as e:
            logger.warning(f"Could not get account balance, using config default: {e}")
            actual_balance = Config.INITIAL_BALANCE
        
        self.risk_manager = AdvancedRiskManager(
            initial_balance=actual_balance,  # ✅ Use actual balance
            daily_loss_limit_pct=0.02,
            max_drawdown_pct=0.10,
            max_loss_streak=3
        )
        self.profit_manager = ProfitManager()
        self.metrics_tracker = MetricsTracker()
        
        # RL predictor (optional)
        self.rl_predictor = None
        self.use_rl = use_rl
        if use_rl and rl_model_path and os.path.exists(rl_model_path):
            try:
                self.rl_predictor = RLPredictor(rl_model_path, agent_type='grpo')
                self.rl_predictor.load_model()
                logger.info("RL predictor loaded")
            except Exception as e:
                logger.warning(f"Failed to load RL model: {e}")
                self.use_rl = False
        
        # Model degrade detector
        self.degrade_detector = ModelDegradeDetector() if self.use_rl else None
        
        # Ensemble predictor
        self.ensemble = EnsemblePredictor()
        
        # News filter
        self.news_filter = NewsFilter()
        
        # Position tracking
        self.positions: Dict[str, Dict] = {}
        
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        try:
            # Update account balance
            account = self.client.get_account()
            self.risk_manager.update_balance(float(account['equity']))
            
            # Monitor existing positions
            self._monitor_positions()
            
            # Scan for new opportunities
            if len(self.positions) < Config.MAX_ACTIVE_TRADES:
                self._scan_and_trade()
            
            # Log status
            self._log_status()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
    
    def _monitor_positions(self):
        """Monitor all open positions"""
        for symbol, position_info in list(self.positions.items()):
            try:
                # Get current price
                current_price = self.client.get_latest_price(symbol)
                if current_price is None:
                    continue
                
                # Check profit manager for exits
                exit_action = self.profit_manager.check_exits(symbol, current_price)
                
                if exit_action:
                    # Execute exit
                    qty = exit_action['qty']
                    order = self.executor.execute_market_order(
                        symbol, qty, 'sell', is_option=False
                    )
                    
                    if order:
                        # Calculate P&L
                        entry_price = position_info['entry_price']
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * qty if position_info['side'] == 'long' else (entry_price - exit_price) * qty
                        
                        # Record trade
                        self.risk_manager.record_trade(
                            symbol, qty, entry_price, exit_price, pnl, position_info['side']
                        )
                        self.metrics_tracker.record_trade(
                            symbol, entry_price, exit_price, qty, position_info['side'],
                            pnl, position_info.get('agent_name')
                        )
                        
                        # Update position
                        position_info['current_qty'] -= qty
                        if position_info['current_qty'] <= 0.01:
                            del self.positions[symbol]
                            self.profit_manager.remove_position(symbol)
                        
                        logger.info(f"Exit executed: {symbol} - {exit_action['reason']}")
                
                # Update trailing stop
                self.profit_manager.update_trailing_stop(symbol, current_price)
                
            except Exception as e:
                logger.error(f"Error monitoring position {symbol}: {e}")
    
    def _scan_and_trade(self):
        """Scan for trading opportunities"""
        if not self.client.is_market_open():
            return
        
        # Check news filter
        is_blocked, reason = self.news_filter.is_blocked()
        if is_blocked:
            logger.info(f"Trading blocked by news filter: {reason}")
            return
        
        # Get risk status
        risk_status = self.risk_manager.get_risk_status()
        
        # Verify risk status against actual account state (safety check)
        if risk_status['risk_level'] in ['danger', 'blocked']:
            # Double-check with actual account balance
            try:
                account = self.client.get_account()
                actual_balance = float(account['equity'])
                actual_equity_pct = (actual_balance / self.risk_manager.initial_balance) if self.risk_manager.initial_balance > 0 else 1.0
                
                # If account is actually healthy (within 5% of initial), reset risk manager
                if actual_equity_pct >= 0.95:
                    logger.info(f"Risk status shows {risk_status['risk_level']} but account is healthy (${actual_balance:,.2f}). Resetting risk manager.")
                    self.risk_manager.peak_balance = max(self.risk_manager.peak_balance, actual_balance)
                    self.risk_manager.current_balance = actual_balance
                    # Re-check risk status
                    risk_status = self.risk_manager.get_risk_status()
                    logger.info(f"Risk status after reset: {risk_status['risk_level']}")
                else:
                    logger.warning(f"Trading blocked: {risk_status['risk_level']} (actual balance: ${actual_balance:,.2f})")
                    return
            except Exception as e:
                logger.warning(f"Trading blocked: {risk_status['risk_level']} (could not verify: {e})")
                return
        
        # Final check after potential reset
        if risk_status['risk_level'] in ['danger', 'blocked']:
            logger.warning(f"Trading blocked: {risk_status['risk_level']}")
            return
        
        # Check model degradation
        if self.degrade_detector:
            is_degraded, reason = self.degrade_detector.check_degradation()
            if is_degraded:
                logger.warning(f"RL model degraded: {reason} - Disabling RL predictions")
                self.use_rl = False
        
        # Analyze each ticker
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        for symbol in Config.TICKERS:
            if symbol in self.positions:
                continue
            
            try:
                # Get historical bars
                bars = self.client.get_historical_bars(
                    symbol, TimeFrame.Day, start_date, end_date
                )
                
                if bars.empty or len(bars) < 50:
                    continue
                
                # Get current price
                current_price = self.client.get_latest_price(symbol)
                if current_price is None:
                    continue
                
                # Get signals from multiple sources
                signals = []
                
                # 1. Multi-agent system
                intent = self.orchestrator.analyze_symbol(symbol, bars)
                if intent and intent.direction != TradeDirection.FLAT:
                    signals.append({
                        'source': 'multi_agent',
                        'direction': intent.direction.value,
                        'confidence': intent.confidence,
                        'agent': intent.agent_name,
                        'reasoning': intent.reasoning
                    })
                
                # 2. RL predictor (if available)
                rl_pred = None
                if self.use_rl and self.rl_predictor:
                    rl_pred = self.rl_predictor.predict(symbol, bars, current_price)
                    if rl_pred['direction'] != 'FLAT' and rl_pred['confidence'] >= 0.6:
                        signals.append({
                            'source': 'rl',
                            'direction': rl_pred['direction'],
                            'confidence': rl_pred['confidence'],
                            'agent': 'RL_Predictor',
                            'reasoning': rl_pred['reason']
                        })
                
                # 3. Use ensemble if we have multiple signals
                if len(signals) > 1:
                    # Extract predictions for ensemble
                    trend_pred = next((s for s in signals if s['source'] == 'multi_agent'), None)
                    ensemble_signal = self.ensemble.combine_predictions(
                        rl_prediction=rl_pred if rl_pred else None,
                        trend_prediction=trend_pred if trend_pred else None
                    )
                    
                    if ensemble_signal['direction'] != 'FLAT':
                        best_signal = {
                            'source': 'ensemble',
                            'direction': ensemble_signal['direction'],
                            'confidence': ensemble_signal['confidence'],
                            'agent': 'Ensemble',
                            'reasoning': ensemble_signal['reason']
                        }
                    else:
                        best_signal = max(signals, key=lambda x: x['confidence'])
                elif signals:
                    best_signal = max(signals, key=lambda x: x['confidence'])
                else:
                    continue
                
                # Check risk (only if we have a signal)
                if 'best_signal' in locals() and best_signal:
                    allowed, reason, risk_level = self.risk_manager.check_trade_allowed(
                        symbol, 10, current_price, 'buy'
                    )
                    
                    if allowed and best_signal['confidence'] >= 0.6:
                        logger.info(f"Executing trade: {symbol} {best_signal['direction']} "
                                  f"(confidence: {best_signal['confidence']:.2f}, agent: {best_signal.get('agent', 'Unknown')})")
                        self._execute_trade(symbol, best_signal, current_price, bars)
                    elif not allowed:
                        logger.debug(f"Trade blocked for {symbol}: {reason}")
                    elif best_signal['confidence'] < 0.6:
                        logger.debug(f"Signal confidence too low for {symbol}: {best_signal['confidence']:.2f} < 0.6")
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
    
    def _execute_trade(
        self,
        symbol: str,
        signal: Dict,
        current_price: float,
        bars: pd.DataFrame
    ):
        """Execute a trade"""
        try:
            # Calculate position size
            account = self.client.get_account()
            balance = float(account['equity'])
            position_size_pct = Config.POSITION_SIZE_PCT
            
            # Use 50% of previous day balance (or current if first trade)
            position_capital = balance * position_size_pct / Config.MAX_ACTIVE_TRADES
            qty = position_capital / current_price
            qty = int(qty) if qty >= 1 else round(qty, 2)
            
            if qty < 0.01:
                return
            
            # Determine side
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            
            # Execute order (or simulate in dry-run)
            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute: {symbol} {side} {qty} @ ${current_price:.2f}")
                order = {
                    'status': 'filled',
                    'filled_avg_price': current_price,
                    'filled_qty': qty
                }
            else:
                order = self.executor.execute_market_order(symbol, qty, side)
            
            if order and order.get('status') == 'filled':
                filled_price = order.get('filled_avg_price', current_price)
                filled_qty = order.get('filled_qty', qty)
                
                # Add to position tracking
                self.positions[symbol] = {
                    'qty': filled_qty,
                    'entry_price': filled_price,
                    'side': 'long' if side == 'buy' else 'short',
                    'agent_name': signal.get('agent', 'Unknown'),
                    'entry_time': datetime.now(),
                    'current_qty': filled_qty
                }
                
                # Add to profit manager
                self.profit_manager.add_position(
                    symbol, filled_qty, filled_price,
                    'long' if side == 'buy' else 'short'
                )
                
                logger.info(f"Trade executed: {symbol} {side} {filled_qty} @ ${filled_price:.2f}")
                logger.info(f"  Signal: {signal['source']} ({signal['agent']})")
                logger.info(f"  Confidence: {signal['confidence']:.2%}")
                
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {e}")
    
    def _log_status(self):
        """Log current status"""
        account = self.client.get_account()
        risk_status = self.risk_manager.get_risk_status()
        metrics = self.metrics_tracker.calculate_metrics(lookback_days=1)
        
        logger.info(f"Status: Balance=${float(account['equity']):,.2f}, "
                   f"Positions={len(self.positions)}, "
                   f"Risk={risk_status['risk_level']}, "
                   f"Daily P&L=${risk_status['daily_pnl']:.2f}")
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        account = self.client.get_account()
        risk_status = self.risk_manager.get_risk_status()
        metrics = self.metrics_tracker.calculate_metrics()
        
        return {
            'account': account,
            'risk': risk_status,
            'metrics': metrics,
            'positions': len(self.positions),
            'rl_enabled': self.use_rl and self.rl_predictor is not None
        }

