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
from core.live.activity_tracker import ActivityTracker
from core.options.option_selector import OptionSelector
from pathlib import Path
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
        self.risk_manager = AdvancedRiskManager(
            initial_balance=Config.INITIAL_BALANCE,
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
        
        # Activity tracker (for dashboard real-time status)
        self.activity_tracker = ActivityTracker()
        
        # Activity heartbeat (keeps activity tracker updated even when idle)
        from core.live.activity_heartbeat import ActivityHeartbeat
        self.activity_heartbeat = ActivityHeartbeat(self.activity_tracker, interval_seconds=30)
        self.activity_heartbeat.start()
        
        # Option selector (for selecting option contracts)
        self.option_selector = OptionSelector(self.client)
        
        # Position tracking
        self.positions: Dict[str, Dict] = {}
        
        # Previous day balance tracking (for 50% position sizing per README)
        self.previous_day_balance_file = Path('daily_balance.json')
        self.previous_day_balance = self._load_previous_balance()
        
    def run_trading_cycle(self):
        """Run one complete trading cycle - Isolated per-run execution"""
        cycle_start = datetime.now()
        logger.info("="*70)
        logger.info(f"🔄 TRADING CYCLE START: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)
        
        # Update activity: cycle starting
        # Always reset at start of cycle (safety: prevents stuck states)
        cycle_id = cycle_start.isoformat()
        self.activity_tracker.update_activity(
            status=ActivityTracker.STATUS_SCANNING,
            message='Starting trading cycle',
            details=f'Scanning {len(Config.TICKERS)} tickers',
            cycle_id=cycle_id,
            step=0,
            total_steps=len(Config.TICKERS)
        )
        
        try:
            # Check pre-conditions
            if not self.client.is_market_open():
                logger.info("⏸️  Market is closed - skipping cycle")
                self.activity_tracker.update_activity(
                    status=ActivityTracker.STATUS_IDLE,
                    message='Market closed',
                    details='Waiting for market to open'
                )
                return
            # Update account balance
            account = self.client.get_account()
            self.risk_manager.update_balance(float(account['equity']))
            
            # Check position limit
            current_positions = len(self.positions)
            if current_positions >= Config.MAX_ACTIVE_TRADES:
                logger.info(f"⏸️  Max positions reached ({current_positions}/{Config.MAX_ACTIVE_TRADES}) - monitoring only")
            
            # Monitor existing positions
            if current_positions > 0:
                self.activity_tracker.update_activity(
                    status=ActivityTracker.STATUS_MONITORING,
                    message='Monitoring positions',
                    details=f'Checking {current_positions} open positions for exits'
                )
            self._monitor_positions()
            
            # Scan for new opportunities (only if under limit)
            if current_positions < Config.MAX_ACTIVE_TRADES:
                self._scan_and_trade()
            else:
                logger.info(f"⏸️  Skipping scan - at position limit ({current_positions}/{Config.MAX_ACTIVE_TRADES})")
            
            # Log status
            self._log_status()
            
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            logger.info(f"🔄 TRADING CYCLE END: Duration={cycle_duration:.2f}s")
            logger.info("="*70)
            
            # Update activity: cycle complete
            self.activity_tracker.update_activity(
                status=ActivityTracker.STATUS_IDLE,
                message='Cycle complete',
                details=f'Completed in {cycle_duration:.1f}s, next cycle in 5 minutes'
            )
            
            # Note: Activity heartbeat will continue updating every 30s to show system is alive
            
        except Exception as e:
            logger.error(f"❌ Error in trading cycle: {e}", exc_info=True)
            self.activity_tracker.update_activity(
                status=ActivityTracker.STATUS_ERROR,
                message='Cycle error',
                details=f'Error: {str(e)[:50]}'
            )
    
    def _monitor_positions(self):
        """Monitor all open positions (handles both stock and option positions)"""
        for symbol, position_info in list(self.positions.items()):
            try:
                # Determine if this is an option position
                # Option symbols are longer and contain expiry/strike info
                is_option = position_info.get('underlying') is not None or len(symbol) > 10
                
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
                        symbol, qty, 'sell', is_option=is_option
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
            logger.info(f"🛡️ Trading blocked by news filter: {reason} (protecting capital during high-risk events)")
            return
        
        # Get risk status
        risk_status = self.risk_manager.get_risk_status()
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
        
        logger.info(f"🔍 SCAN START: Analyzing {len(Config.TICKERS)} tickers")
        
        # Update activity: scan starting
        # Always reset to SCANNING at start of scan (safety: prevents stuck EXECUTING state)
        self.activity_tracker.update_activity(
            status=ActivityTracker.STATUS_SCANNING,
            message='Scanning tickers',
            details=f'Analyzing {len(Config.TICKERS)} tickers for opportunities',
            step=0,
            total_steps=len(Config.TICKERS)
        )
        
        scan_results = {
            'scanned': 0,
            'data_unavailable': 0,
            'signals_found': 0,
            'trades_executed': 0,
            'errors': 0
        }
        
        for symbol in Config.TICKERS:
            # One-trade-per-symbol rule: Skip if already have position for this underlying
            has_existing_position = symbol in self.positions
            if not has_existing_position:
                # Check if we have an option position for this underlying
                for pos_symbol in self.positions.keys():
                    if pos_symbol.startswith(symbol) and len(pos_symbol) > len(symbol):
                        pos_data = self.positions[pos_symbol]
                        underlying = pos_data.get('underlying', '')
                        if underlying == symbol:
                            has_existing_position = True
                            break
            
            if has_existing_position:
                logger.debug(f"⏭️  {symbol}: Skipping (already have position - one-trade-per-symbol rule)")
                continue
            
            # Update activity: current ticker being analyzed
            scan_results['scanned'] += 1
            self.activity_tracker.update_activity(
                status=ActivityTracker.STATUS_ANALYZING,
                ticker=symbol,
                message=f'Analyzing {symbol}',
                details=f'Evaluating {symbol} for trading signals',
                step=scan_results['scanned'],
                total_steps=len(Config.TICKERS)
            )
            
            # Reset to analyzing after any execution completes (safety check)
            # This ensures we don't get stuck in EXECUTING state
            
            try:
                # Get historical bars
                bars = self.client.get_historical_bars(
                    symbol, TimeFrame.Day, start_date, end_date
                )
                
                # Minimum bars required: 30 (reduced from 50 to account for weekends/holidays)
                # 30 bars = ~6 weeks of trading days, sufficient for all indicators
                min_bars_required = 30
                if bars.empty or len(bars) < min_bars_required:
                    scan_results['data_unavailable'] += 1
                    error_msg = f"data_unavailable: insufficient bars ({len(bars) if not bars.empty else 0} bars, need {min_bars_required}+)"
                    logger.warning(f"⚠️  {symbol}: {error_msg}")
                    logger.info(f"[SKIP] {symbol} | reason=DATA_UNAVAILABLE | "
                              f"bars={len(bars) if not bars.empty else 0} | "
                              f"need={min_bars_required}+")
                    continue
                
                # Log successful data load
                logger.debug(f"✅ {symbol}: Data available ({len(bars)} bars) - proceeding to analysis")
                
                # Get current price
                current_price = self.client.get_latest_price(symbol)
                if current_price is None:
                    continue
                
                # Get signals from multiple sources
                signals = []
                
                # 1. Multi-agent system
                intent = self.orchestrator.analyze_symbol(symbol, bars)
                if intent and intent.direction != TradeDirection.FLAT:
                    logger.info(f"[SIGNAL] {symbol} | source=multi_agent | "
                              f"action={intent.direction.value} | "
                              f"confidence={intent.confidence:.2f} | "
                              f"agent={intent.agent_name}")
                    signals.append({
                        'source': 'multi_agent',
                        'direction': intent.direction.value,
                        'confidence': intent.confidence,
                        'agent': intent.agent_name,
                        'reasoning': intent.reasoning
                    })
                elif intent and intent.direction == TradeDirection.FLAT:
                    logger.info(f"[SIGNAL] {symbol} | source=multi_agent | "
                              f"action=FLAT | confidence={intent.confidence:.2f} | "
                              f"reason=agent_returned_flat")
                
                # 2. RL predictor (if available)
                rl_pred = None
                if self.use_rl and self.rl_predictor:
                    rl_pred = self.rl_predictor.predict(symbol, bars, current_price)
                    # Threshold: 0.5 (50%) - Professional conservative level
                    if rl_pred['direction'] != 'FLAT' and rl_pred['confidence'] >= 0.5:
                        logger.info(f"🧠 {symbol}: RL predictor generated {rl_pred['direction']} signal "
                                   f"(confidence: {rl_pred['confidence']:.2f}, reason: {rl_pred['reason'][:60] if rl_pred.get('reason') else 'N/A'})")
                        signals.append({
                            'source': 'rl',
                            'direction': rl_pred['direction'],
                            'confidence': rl_pred['confidence'],
                            'agent': 'RL_Predictor',
                            'reasoning': rl_pred['reason']
                        })
                    elif rl_pred['direction'] != 'FLAT':
                        logger.debug(f"⏳ {symbol}: RL signal confidence too low: {rl_pred['confidence']:.2f} < 0.50 (waiting for stronger signal)")
                    else:
                        logger.debug(f"⏸️  {symbol}: RL predictor: FLAT (no directional bias)")
                
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
                    logger.info(f"[SIGNAL] {symbol} | has_signal=False | "
                              f"action=None | confidence=0.00 | "
                              f"reason=no_signals_from_any_source")
                    logger.info(f"[SKIP] {symbol} | reason=NO_SIGNAL | "
                              f"conf=0.00 | risk_ok=N/A | "
                              f"has_position={symbol in self.positions}")
                    continue
                
                # Check risk (only if we have a signal)
                if 'best_signal' in locals() and best_signal:
                    logger.info(f"📈 {symbol}: Best signal selected - {best_signal.get('agent', 'Unknown')} "
                               f"({best_signal['direction']}, confidence: {best_signal['confidence']:.2f})")
                    allowed, reason, risk_level = self.risk_manager.check_trade_allowed(
                        symbol, 10, current_price, 'buy'
                    )
                    
                    # Confidence threshold: 0.5 (50%) - Professional conservative level
                    confidence_threshold = 0.5
                    
                    # Check if already have position (check both stock and option positions)
                    # Since we now trade options, check if we have any position for this underlying
                    has_position = symbol in self.positions  # Direct symbol match
                    if not has_position:
                        # Check if we have an option position for this underlying
                        for pos_symbol in self.positions.keys():
                            # If position is an option, check if underlying matches
                            if pos_symbol.startswith(symbol) and len(pos_symbol) > len(symbol):
                                # This is likely an option position for this underlying
                                pos_data = self.positions[pos_symbol]
                                underlying = pos_data.get('underlying', '')
                                if underlying == symbol:
                                    has_position = True
                                    break
                    
                    # Determine skip reason
                    skip_reason = None
                    if not allowed:
                        skip_reason = f"RISK_BLOCK: {reason}"
                    elif best_signal['confidence'] < confidence_threshold:
                        skip_reason = f"LOW_CONFIDENCE: {best_signal['confidence']:.2f} < {confidence_threshold}"
                    elif has_position:
                        skip_reason = "HAS_POSITION: one-trade-per-symbol rule"
                    
                    # Log signal evaluation for monitoring
                    logger.info(f"📊 Signal evaluation for {symbol}: "
                              f"confidence={best_signal['confidence']:.2f}, "
                              f"agent={best_signal.get('agent', 'Unknown')}, "
                              f"direction={best_signal['direction']}, "
                              f"allowed={allowed}")
                    
                    # Log skip reason if trade won't execute
                    if skip_reason:
                        logger.info(f"[SKIP] {symbol} | reason={skip_reason} | "
                                  f"conf={best_signal['confidence']:.2f} | "
                                  f"risk_ok={allowed} | "
                                  f"has_position={has_position}")
                    
                    if allowed and best_signal['confidence'] >= confidence_threshold and not has_position:
                        scan_results['signals_found'] += 1
                        logger.info(f"✅ EXECUTING TRADE: {symbol} {best_signal['direction']} "
                                  f"(confidence: {best_signal['confidence']:.2f}, agent: {best_signal.get('agent', 'Unknown')}, "
                                  f"reasoning: {best_signal.get('reasoning', 'N/A')[:50]})")
                        
                        # Update activity: executing trade
                        self.activity_tracker.update_activity(
                            status=ActivityTracker.STATUS_EXECUTING,
                            ticker=symbol,
                            message=f'Executing trade – {symbol}',
                            details=f'{best_signal["direction"]} @ {best_signal["confidence"]:.1%} confidence'
                        )
                        
                        try:
                            self._execute_trade(symbol, best_signal, current_price, bars)
                            scan_results['trades_executed'] += 1
                            
                            # Update activity: execution complete, continue scanning
                            self.activity_tracker.update_activity(
                                status=ActivityTracker.STATUS_ANALYZING,
                                ticker=symbol,
                                message=f'Trade executed – {symbol}',
                                details=f'Continuing scan...',
                                step=scan_results['scanned'],
                                total_steps=len(Config.TICKERS)
                            )
                        except Exception as exec_error:
                            logger.error(f"❌ Error executing trade for {symbol}: {exec_error}")
                            # Update activity: execution failed, continue scanning
                            self.activity_tracker.update_activity(
                                status=ActivityTracker.STATUS_ANALYZING,
                                ticker=symbol,
                                message=f'Trade execution failed – {symbol}',
                                details=f'Error: {str(exec_error)[:50]}',
                                step=scan_results['scanned'],
                                total_steps=len(Config.TICKERS)
                            )
                    # Skip reasons are already logged above with [SKIP] tag
                    pass
                
            except Exception as e:
                scan_results['errors'] += 1
                error_msg = str(e)
                if "subscription" in error_msg.lower() or "sip" in error_msg.lower():
                    logger.warning(f"⚠️  {symbol}: data_unavailable: {error_msg[:80]}")
                else:
                    logger.error(f"❌ {symbol}: Error during scan - {error_msg[:80]}")
                # Continue to next ticker - don't let one failure break the whole scan
        
        # Log scan summary
        logger.info(f"🔍 SCAN END: Scanned={scan_results['scanned']}, "
                   f"DataUnavailable={scan_results['data_unavailable']}, "
                   f"Signals={scan_results['signals_found']}, "
                   f"TradesExecuted={scan_results['trades_executed']}, "
                   f"Errors={scan_results['errors']}")
        
        # Update activity: scan complete
        self.activity_tracker.update_activity(
            status=ActivityTracker.STATUS_IDLE,
            message='Scan complete',
            details=f"Found {scan_results['signals_found']} signals, executed {scan_results['trades_executed']} trades",
            step=scan_results['scanned'],
            total_steps=len(Config.TICKERS)
        )
    
    def _load_previous_balance(self) -> float:
        """Load previous day's ending balance"""
        try:
            if self.previous_day_balance_file.exists():
                import json
                with open(self.previous_day_balance_file, 'r') as f:
                    data = json.load(f)
                    return float(data.get('balance', Config.INITIAL_BALANCE))
        except Exception as e:
            logger.warning(f"Error loading previous balance: {e}")
        
        # Fallback to current balance if no previous day data
        try:
            account = self.client.get_account()
            return float(account['equity'])
        except:
            return Config.INITIAL_BALANCE
    
    def _execute_trade(
        self,
        symbol: str,
        signal: Dict,
        current_price: float,
        bars: pd.DataFrame
    ):
        """Execute an OPTION trade - Uses 50% of previous day's ending balance per README"""
        try:
            # Get current account info
            account = self.client.get_account()
            current_balance = float(account['equity'])
            
            # Use 50% of previous day's ending balance (per README criteria)
            # If no previous day data, use 50% of current balance
            base_balance = self.previous_day_balance if self.previous_day_balance > 0 else current_balance
            position_capital = base_balance * 0.50  # 50% of previous day balance
            
            # Divide by max active trades to size each position
            position_capital_per_trade = position_capital / Config.MAX_ACTIVE_TRADES
            
            # Determine side
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            
            # ✅ NEW: Select option contract
            logger.info(f"🔍 Selecting option contract for {symbol} ({signal['direction']})")
            option_contract = self.option_selector.pick_best_option(
                ticker=symbol,
                side=side,
                current_price=current_price,
                max_dte=7,  # Prefer 0-7 DTE, but will accept up to 30
                min_price=0.20,
                max_price=10.00
            )
            
            if not option_contract:
                logger.warning(f"⚠️  {symbol}: No suitable option contract found - skipping trade")
                return
            
            option_symbol = option_contract['symbol']
            option_price = option_contract['price']
            option_strike = option_contract['strike']
            option_dte = option_contract['dte']
            option_type = option_contract['type'].upper()
            
            logger.info(f"✅ Selected option: {option_symbol}")
            logger.info(f"   Strike: ${option_strike:.2f} | DTE: {option_dte} | Type: {option_type}")
            logger.info(f"   Price: ${option_price:.2f} | Bid: ${option_contract['bid']:.2f} | Ask: ${option_contract['ask']:.2f}")
            
            # Recalculate quantity for options (options are whole contracts)
            # Options are priced per contract (e.g., $2.50 per contract)
            qty = int(position_capital_per_trade / option_price)  # Whole contracts only
            
            if qty < 1:
                logger.warning(f"Position size too small for {option_symbol}: {qty} contracts "
                             f"(price: ${option_price:.2f}, capital: ${position_capital_per_trade:.2f})")
                return
            
            logger.info(f"📊 Position sizing for {option_symbol}: "
                       f"Previous day balance: ${base_balance:,.2f}, "
                       f"50% allocation: ${position_capital:,.2f}, "
                       f"Per trade: ${position_capital_per_trade:,.2f}, "
                       f"Quantity: {qty} contracts @ ${option_price:.2f}")
            
            # Execute OPTION order (or simulate in dry-run)
            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute OPTION: {option_symbol} {side.upper()} {qty} contracts @ ${option_price:.2f}")
                order = {
                    'status': 'filled',
                    'filled_avg_price': option_price,
                    'filled_qty': qty
                }
            else:
                # ✅ KEY CHANGE: Execute as OPTION trade
                order = self.executor.execute_market_order(option_symbol, qty, side, is_option=True)
            
            if order and order.get('status') == 'filled':
                filled_price = order.get('filled_avg_price', option_price)
                filled_qty = order.get('filled_qty', qty)
                
                # Add to position tracking (use option symbol, not stock symbol)
                self.positions[option_symbol] = {
                    'qty': filled_qty,
                    'entry_price': filled_price,
                    'side': 'long' if side == 'buy' else 'short',
                    'agent_name': signal.get('agent', 'Unknown'),
                    'entry_time': datetime.now(),
                    'current_qty': filled_qty,
                    'underlying': symbol,  # Track underlying for reference
                    'strike': option_strike,
                    'expiry': option_contract['expiry'],
                    'dte': option_dte,
                    'option_type': option_type
                }
                
                # Add to profit manager (use option symbol)
                self.profit_manager.add_position(
                    option_symbol, filled_qty, filled_price,
                    'long' if side == 'buy' else 'short'
                )
                
                logger.info(f"✅ OPTION TRADE EXECUTED: {option_symbol} {side.upper()} {filled_qty} contracts @ ${filled_price:.2f}")
                logger.info(f"   Underlying: {symbol} | Strike: ${option_strike:.2f} | DTE: {option_dte}")
                logger.info(f"   Signal: {signal['source']} ({signal['agent']})")
                logger.info(f"   Confidence: {signal['confidence']:.2%}")
                
        except Exception as e:
            logger.error(f"❌ Error executing option trade for {symbol}: {e}", exc_info=True)
    
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

