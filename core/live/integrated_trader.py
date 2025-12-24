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
        
        # Initialize Massive price feed (if available)
        self.massive_price_feed = None
        try:
            from services.massive_price_feed import MassivePriceFeed
            self.massive_price_feed = MassivePriceFeed()
            if self.massive_price_feed.is_available():
                logger.info("Massive price feed initialized and available")
            else:
                logger.warning("Massive price feed initialized but API key not configured")
        except Exception as e:
            logger.warning(f"Could not initialize Massive price feed: {e}, will use Alpaca")
        
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
            max_loss_streak=3,
            use_iv_regimes=True
        )
        
        # Enable UVaR checking
        self.risk_manager.enable_uvar(self.client, max_uvar_pct=5.0)
        
        # Update calendars for Gap Risk Monitor
        self._update_calendars()
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
        
        # Option Universe Filter (Phase-0: Filter BEFORE signals)
        from core.live.option_universe_filter import OptionUniverseFilter
        self.option_filter = OptionUniverseFilter(
            max_spread_pct=20.0,
            min_bid=0.01,
            min_bid_size=1,
            max_quote_age_seconds=5.0
        )
        
        # Daily trade budget removed - no limit on trades per day
        
        # Massive price feed (for historical bars)
        self.massive_price_feed = None
        try:
            from services.massive_price_feed import MassivePriceFeed
            self.massive_price_feed = MassivePriceFeed()
            if self.massive_price_feed.is_available():
                logger.info("Massive price feed initialized - will use for historical bars")
            else:
                logger.warning("Massive price feed not available - will fallback to Alpaca")
        except Exception as e:
            logger.warning(f"Could not initialize Massive price feed: {e} - will use Alpaca")
    
    def _update_calendars(self):
        """Update earnings and macro event calendars"""
        try:
            from services.earnings_calendar import EarningsCalendar
            from services.macro_calendar import MacroCalendar
            
            earnings_cal = EarningsCalendar()
            macro_cal = MacroCalendar()
            
            # Update earnings calendar
            if self.risk_manager.use_gap_risk and self.risk_manager.gap_risk_monitor:
                earnings_cal.update_gap_risk_monitor(
                    self.risk_manager.gap_risk_monitor,
                    Config.TICKERS,
                    lookahead_days=90
                )
                logger.info("Updated earnings calendar")
            
            # Update macro calendar
            if self.risk_manager.use_gap_risk and self.risk_manager.gap_risk_monitor:
                macro_cal.update_gap_risk_monitor(
                    self.risk_manager.gap_risk_monitor,
                    lookahead_days=90
                )
                logger.info("Updated macro event calendar")
        except Exception as e:
            logger.warning(f"Could not update calendars: {e}")
        
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        try:
            logger.info("="*60)
            logger.info("TRADING CYCLE STARTED")
            logger.info("="*60)
            
            # Update account balance
            account = self.client.get_account()
            self.risk_manager.update_balance(float(account['equity']))
            logger.info(f"Account balance updated: ${float(account['equity']):,.2f}")
            
            # Monitor existing positions
            self._monitor_positions()
            logger.info(f"Current positions: {len(self.positions)}")
            
            # Scan for new opportunities
            if len(self.positions) < Config.MAX_ACTIVE_TRADES:
                logger.info(f"Position limit check: {len(self.positions)} < {Config.MAX_ACTIVE_TRADES} - Calling _scan_and_trade()")
                self._scan_and_trade()
            else:
                logger.info(f"Position limit reached: {len(self.positions)} >= {Config.MAX_ACTIVE_TRADES} - Skipping scan")
            
            # Log status
            self._log_status()
            
            logger.info("TRADING CYCLE COMPLETED")
            logger.info("="*60)
            
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
                    # Check if this is an options position
                    is_option = position_info.get('instrument_type') == 'option'
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
        logger.info("_scan_and_trade() called - Starting scan")
        
        if not self.client.is_market_open():
            logger.info("Market is closed - Exiting scan")
            return
        
        logger.info("Market is open - Proceeding with scan")
        
        # Check news filter
        is_blocked, reason = self.news_filter.is_blocked()
        if is_blocked:
            logger.warning(f"Trading blocked by news filter: {reason}")
            return
        
        logger.info("News filter check passed")
        
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
        logger.info(f"Scanning {len(Config.TICKERS)} tickers: {', '.join(Config.TICKERS)}")
        signals_found = 0
        signals_checked = 0
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        for symbol in Config.TICKERS:
            signals_checked += 1
            # Check if we already have an option position for this underlying
            has_position = False
            for pos_symbol in self.positions.keys():
                pos = self.positions[pos_symbol]
                if pos.get('underlying') == symbol or pos_symbol == symbol:
                    has_position = True
                    break
            if has_position:
                logger.debug(f"Skipping {symbol} - already have position")
                continue
            
            try:
                # Get historical bars - prefer Massive, fallback to Alpaca
                bars = None
                
                if self.massive_price_feed and self.massive_price_feed.is_available():
                    try:
                        # Use Massive to get daily bars (aggregated from 1-minute)
                        bars = self.massive_price_feed.get_daily_bars(
                            symbol, start_date, end_date, use_1min_aggregation=True
                        )
                        if not bars.empty:
                            logger.debug(f"Got {len(bars)} daily bars from Massive for {symbol}")
                    except Exception as e:
                        logger.warning(f"Error getting bars from Massive for {symbol}: {e}, falling back to Alpaca")
                
                # Fallback to Alpaca if Massive failed or not available
                if bars is None or bars.empty:
                bars = self.client.get_historical_bars(
                    symbol, TimeFrame.Day, start_date, end_date
                )
                    if not bars.empty:
                        logger.debug(f"Got {len(bars)} daily bars from Alpaca for {symbol}")
                
                if bars.empty or len(bars) < 30:  # Reduced from 50 to 30 (with Massive, should always have enough)
                    logger.warning(f"Insufficient data for {symbol}: {len(bars)} bars (need 30+)")
                    continue
                
                # Get current price
                current_price = self.client.get_latest_price(symbol)
                if current_price is None:
                    continue
                
                # Get signals from multiple sources
                signals = []
                
                # 1. Multi-agent system
                logger.debug(f"Analyzing {symbol}...")
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
                    # Phase-0: Raise confidence threshold to 0.7 (70%)
                    if rl_pred['direction'] != 'FLAT' and rl_pred['confidence'] >= 0.7:
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
                    signals_found += 1
                    logger.info(f"Signal found for {symbol}: {best_signal['direction']} @ {best_signal['confidence']:.2%} ({best_signal.get('agent', 'Unknown')})")
                    
                    # BUY OPTIONS (0-30 DTE) - NO STOCKS, NO SELLING
                    # LONG signals → Buy CALL options
                    # SHORT signals → Buy PUT options
                    
                    if best_signal['direction'] not in ['LONG', 'SHORT']:
                        logger.info(f"⚠️  Skipping {symbol}: Signal direction must be LONG or SHORT (got {best_signal['direction']})")
                        continue
                    
                    # Determine option type based on signal direction
                    option_type = 'call' if best_signal['direction'] == 'LONG' else 'put'
                    side = 'buy'  # Always buy (options only)
                    
                    logger.info(f"✅ Signal for {symbol}: {best_signal['direction']} → Buying {option_type.upper()} options")
                    logger.info(f"   Side: {side}, Option Type: {option_type}")
                    
                    # Get IV Rank for risk check
                    iv_rank = None
                    try:
                        from services.iv_rank_service import IVRankService
                        iv_service = IVRankService()
                        metrics = iv_service.get_iv_metrics(symbol)
                        iv_rank = metrics.get('iv_rank')
                    except:
                        pass
                    
                    # Calculate position size for risk check
                    account = self.client.get_account()
                    balance = float(account['equity'])
                    position_size_pct = Config.POSITION_SIZE_PCT
                    position_capital = balance * position_size_pct / Config.MAX_ACTIVE_TRADES
                    qty = position_capital / current_price
                    qty = int(qty) if qty >= 1 else round(qty, 2)
                    
                    # Get current positions for UVaR
                    positions = self.client.get_positions()
                    current_positions = []
                    for pos in positions:
                        current_positions.append({
                            'symbol': pos['symbol'],
                            'qty': float(pos['qty']),
                            'entry_price': pos.get('avg_entry_price', 0),
                            'current_price': pos.get('current_price', 0)
                        })
                    
                    allowed, reason, risk_level = self.risk_manager.check_trade_allowed(
                        symbol=symbol,
                        qty=qty,
                        price=current_price,
                        side=side,
                        iv_rank=iv_rank,
                        current_positions=current_positions
                    )
                    
                    if allowed and best_signal['confidence'] >= 0.6:
                        logger.info(f"✅ EXECUTING TRADE: {symbol} {best_signal['direction']} "
                                  f"(confidence: {best_signal['confidence']:.2%}, agent: {best_signal.get('agent', 'Unknown')})")
                        logger.info(f"   Side: {side}, Qty: {qty}, Price: ${current_price:.2f}")
                        self._execute_trade(symbol, best_signal, current_price, bars)
                    elif not allowed:
                        logger.warning(f"❌ Trade BLOCKED for {symbol}: {reason} (risk_level: {risk_level})")
                    elif best_signal['confidence'] < 0.7:  # Raised from 0.6 to 0.7
                        logger.info(f"⚠️  Signal confidence too low for {symbol}: {best_signal['confidence']:.2%} < 0.7")
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
        
        logger.info(f"Scan complete: {signals_found} signals found out of {signals_checked} tickers checked")
    
    def _execute_trade(
        self,
        symbol: str,
        signal: Dict,
        current_price: float,
        bars: pd.DataFrame
    ):
        """Execute an OPTIONS trade (0-30 DTE, BUY ONLY)
        
        LONG signals → Buy CALL options
        SHORT signals → Buy PUT options
        """
        try:
            # Validate signal direction
            if signal['direction'] not in ['LONG', 'SHORT']:
                logger.warning(f"Skipping {symbol}: Signal direction must be LONG or SHORT (got {signal['direction']})")
                return
            
            # Determine option type: LONG = calls, SHORT = puts
            option_type = 'call' if signal['direction'] == 'LONG' else 'put'
            logger.info(f"Executing {signal['direction']} signal for {symbol} → Buying {option_type.upper()} options")
            
            # Get options data feed (requires alpaca_client)
            from services.options_data_feed import OptionsDataFeed
            options_feed = OptionsDataFeed(self.client)
            
            # Get expiration dates
            expirations = options_feed.get_expiration_dates(symbol)
            if not expirations:
                logger.warning(f"No expiration dates found for {symbol}")
                return
            
            # Select expiration (0-30 DTE)
            from datetime import datetime, timedelta
            today = datetime.now().date()
            target_expiration = None
            
            for exp_date in sorted(expirations):
                if isinstance(exp_date, str):
                    exp_date = datetime.strptime(exp_date, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                if Config.MIN_DTE <= dte <= Config.MAX_DTE:
                    target_expiration = exp_date
                    break
            
            if not target_expiration:
                logger.warning(f"No expiration found for {symbol} in {Config.MIN_DTE}-{Config.MAX_DTE} DTE range")
                return
            
            logger.info(f"Selected expiration for {symbol}: {target_expiration} (DTE: {(target_expiration - today).days})")
            
            # Phase-0: Get options chain FIRST, then filter for liquidity
            # This ensures we only consider tradable options BEFORE selecting ATM
            exp_date_str = target_expiration.strftime('%Y-%m-%d') if isinstance(target_expiration, datetime) else str(target_expiration)
            options_chain = options_feed.get_options_chain(symbol, exp_date_str)
            
            if not options_chain:
                logger.warning(f"No options chain found for {symbol} expiring {target_expiration}")
                return
            
            # Phase-0: Filter options chain for liquidity BEFORE selecting ATM
            liquid_options = self.option_filter.filter_options_chain(options_chain)
            
            if not liquid_options:
                logger.warning(f"No liquid options found for {symbol} expiring {target_expiration} after liquidity filter")
                return
            
            # Filter for option type (call/put)
            filtered_by_type = [opt for opt in liquid_options if opt.get('type', '').lower() == option_type]
            
            if not filtered_by_type:
                logger.warning(f"No liquid {option_type} options found for {symbol} after type filter")
                return
            
            # Get ATM option from filtered, liquid options
            # LONG signal → Buy CALL options
            # SHORT signal → Buy PUT options
            option_contract = options_feed.get_atm_options(
                symbol,
                exp_date_str,
                option_type,  # 'call' for LONG, 'put' for SHORT
                available_contracts=filtered_by_type  # Only consider liquid options
            )
            
            if not option_contract:
                logger.warning(f"No ATM {option_type} option found for {symbol} expiring {target_expiration} in liquid options")
                return
            
            # Phase-0: Verify selected option is still liquid
            is_tradable, reason = self.option_filter.is_option_tradable(option_contract)
            if not is_tradable:
                logger.warning(f"Selected ATM option failed liquidity check: {reason}")
                return
            
            # Get option symbol directly from contract data (Alpaca/Massive)
            # DO NOT construct - use actual data from API
            option_symbol = (
                option_contract.get('symbol') or 
                option_contract.get('contract_symbol') or
                option_contract.get('ticker') or
                option_contract.get('name') or
                option_contract.get('id')
            )
            
            if not option_symbol:
                logger.error(f"No option symbol found in contract data for {symbol}")
                logger.error(f"Contract keys: {list(option_contract.keys())}")
                logger.error(f"Contract data: {option_contract}")
                return
            
            # Clean up symbol if needed (remove prefixes like "O:" from Massive)
            if isinstance(option_symbol, str):
                option_symbol = option_symbol.replace('O:', '').strip().upper()
            
            logger.info(f"Using option symbol from contract data: {option_symbol}")
            logger.debug(f"Contract details: strike={option_contract.get('strike_price')}, type={option_contract.get('type')}, expiration={target_expiration}")
            
            # Try to get quote from Massive first (data provider)
            option_price = None
            quote_source = None
            
            # Method 1: Use Massive for quotes (data provider)
            try:
                from services.polygon_options_feed import MassiveOptionsFeed
                massive_feed = MassiveOptionsFeed()
                if massive_feed.is_available():
                    # Get options chain which includes prices
                    exp_date_str = target_expiration.strftime('%Y-%m-%d') if isinstance(target_expiration, datetime) else str(target_expiration)
                    chain = massive_feed.get_options_chain(symbol, expiration_date=exp_date_str)
                    
                    # Get strike from option contract
                    contract_strike = float(option_contract.get('strike_price', 0))
                    
                    # Find the specific option in the chain by matching strike
                    for contract in chain:
                        details = contract.get('details', {})
                        strike = float(details.get('strike_price', 0))
                        option_type = details.get('contract_type', '').lower()
                        
                        # Match by strike (within $0.01) and type (call or put based on signal)
                        if abs(strike - contract_strike) < 0.01 and details.get('contract_type', '').lower() == option_type:
                            # Extract price from Massive data
                            day_data = contract.get('day', {})
                            prev_data = contract.get('prev_day', {})
                            
                            # Try close, then previous close, then open
                            option_price = (
                                day_data.get('close') or
                                prev_data.get('close') or
                                day_data.get('open') or
                                day_data.get('last') or
                                None
                            )
                            
                            if option_price:
                                option_price = float(option_price)
                                quote_source = "Massive"
                                logger.info(f"Got price from Massive for {option_symbol} (strike ${strike}): ${option_price:.2f}")
                                break
            except Exception as e:
                logger.debug(f"Could not get quote from Massive: {e}")
            
            # Method 2: Fallback to Alpaca quote API
            if not option_price:
                try:
                    quote = options_feed.get_option_quote(option_symbol)
                    if quote:
                        option_price = quote.get('last_price') or quote.get('mid_price')
                        if not option_price:
                            bid = quote.get('bid', 0)
                            ask = quote.get('ask', 0)
                            if bid > 0 and ask > 0:
                                option_price = (bid + ask) / 2
                                quote_source = "Alpaca (mid)"
                            else:
                                quote_source = None
                        else:
                            quote_source = "Alpaca"
                except Exception as e:
                    logger.debug(f"Could not get quote from Alpaca: {e}")
            
            # Method 3: Use close price from contract data as last resort
            if not option_price:
                close_price = option_contract.get('close_price')
                if close_price:
                    try:
                        option_price = float(close_price)
                        quote_source = "Contract close_price"
                        logger.info(f"Using close_price from contract for {option_symbol}: ${option_price:.2f}")
                    except:
                        pass
            
            if not option_price or option_price <= 0:
                logger.warning(f"No valid price found for option {option_symbol} (tried Massive, Alpaca, contract data)")
                return
            
            logger.info(f"Option price for {option_symbol}: ${option_price:.2f} (source: {quote_source})")
            
            # Calculate position size (in contracts, not shares)
            account = self.client.get_account()
            balance = float(account['equity'])
            position_size_pct = Config.POSITION_SIZE_PCT
            
            # For options, use higher position size (options are more capital efficient)
            # Options allow leverage, so we can allocate more per trade
            options_position_pct = min(position_size_pct * 1.5, 0.75)  # Up to 75% per options trade
            
            # Position capital per trade (higher for options)
            position_capital = balance * options_position_pct / Config.MAX_ACTIVE_TRADES
            
            # Calculate number of contracts (each contract = 100 shares)
            contract_cost = option_price * 100
            contracts = int(position_capital / contract_cost)
            
            if contracts < 1:
                logger.warning(f"⚠️  Position size too small for {symbol}: ${position_capital:.2f} < ${contract_cost:.2f} (1 contract)")
                logger.warning(f"   Option price: ${option_price:.2f}, Need at least ${contract_cost:.2f} per contract")
                logger.info(f"   💡 Trying OTM options (cheaper premiums) for {symbol}...")
                
                # Try OTM options (cheaper premiums) - 5% OTM
                current_stock_price = self.client.get_latest_price(symbol)
                if current_stock_price:
                    otm_strike = current_stock_price * 1.05  # 5% OTM
                    # Get all options for this expiration and find closest to OTM strike
                    chain = options_feed.get_options_chain(
                        symbol,
                        target_expiration.strftime('%Y-%m-%d') if isinstance(target_expiration, datetime) else str(target_expiration)
                    )
                    
                    # Filter for option type (call for LONG, put for SHORT) and find closest to OTM strike
                    # For LONG: OTM = above current price (calls)
                    # For SHORT: OTM = below current price (puts)
                    if signal['direction'] == 'LONG':
                        # LONG → Calls → OTM strike above current price
                        otm_strike = current_stock_price * 1.05  # 5% OTM
                        filtered_options = [c for c in chain if c.get('type', '').lower() == 'call']
                    else:
                        # SHORT → Puts → OTM strike below current price
                        otm_strike = current_stock_price * 0.95  # 5% OTM
                        filtered_options = [c for c in chain if c.get('type', '').lower() == 'put']
                    
                    if filtered_options:
                        otm_option = min(
                            filtered_options,
                            key=lambda x: abs(float(x.get('strike_price', 0)) - otm_strike)
                        )
                        
                        # Get price for OTM option from Massive
                        otm_price = None
                        try:
                            from services.polygon_options_feed import MassiveOptionsFeed
                            massive_feed = MassiveOptionsFeed()
                            if massive_feed.is_available():
                                massive_chain = massive_feed.get_options_chain(
                                    symbol, 
                                    target_expiration.strftime('%Y-%m-%d') if isinstance(target_expiration, datetime) else str(target_expiration)
                                )
                                otm_strike_val = float(otm_option.get('strike_price', 0))
                                for contract in massive_chain:
                                    details = contract.get('details', {})
                                    if abs(float(details.get('strike_price', 0)) - otm_strike_val) < 0.01:
                                        day_data = contract.get('day', {})
                                        otm_price = day_data.get('close') or day_data.get('open')
                                        if otm_price:
                                            otm_price = float(otm_price)
                                            break
                        except Exception as e:
                            logger.debug(f"Could not get OTM price from Massive: {e}")
                        
                        # Fallback to contract data
                        if not otm_price:
                            otm_price = otm_option.get('close_price') or otm_option.get('last_price')
                            if otm_price:
                                try:
                                    otm_price = float(otm_price)
                                except:
                                    otm_price = None
                        
                        if otm_price and otm_price > 0:
                            otm_contract_cost = otm_price * 100
                            otm_contracts = int(position_capital / otm_contract_cost)
                            if otm_contracts >= 1:
                                logger.info(f"✅ Found affordable OTM option: ${otm_price:.2f} (${otm_contract_cost:.2f}/contract, {otm_contracts} contracts)")
                                option_price = otm_price
                                option_contract = otm_option
                                contracts = otm_contracts
                                
                                # Get OTM option symbol directly from contract data (DO NOT construct)
                                option_symbol = (
                                    otm_option.get('symbol') or 
                                    otm_option.get('contract_symbol') or
                                    otm_option.get('ticker') or
                                    otm_option.get('name') or
                                    otm_option.get('id')
                                )
                                
                                if not option_symbol:
                                    logger.error(f"No option symbol found in OTM contract data for {symbol}")
                                    return
                                
                                # Clean up symbol if needed (remove prefixes like "O:" from Massive)
                                if isinstance(option_symbol, str):
                                    option_symbol = option_symbol.replace('O:', '').strip().upper()
                                
                                logger.info(f"Using OTM {option_type.upper()} option symbol from contract data: {option_symbol}")
                            else:
                                logger.warning(f"   OTM option still too expensive: ${otm_contract_cost:.2f} > ${position_capital:.2f}")
                                return
                        else:
                            logger.warning(f"   Could not get price for OTM option")
                            return
                    else:
                        logger.warning(f"   No {option_type} options available for {symbol}")
                        return
                else:
                    logger.warning(f"   Could not get current stock price for {symbol}")
                return
            
            logger.info(f"Executing OPTIONS trade: {option_symbol} (BUY {contracts} {option_type.upper()} contracts @ ${option_price:.2f})")
            
            # Execute order (or simulate in dry-run)
            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute: {option_symbol} BUY {contracts} contracts @ ${option_price:.2f}")
                order = {
                    'status': 'filled',
                    'filled_avg_price': option_price,
                    'filled_qty': contracts,
                    'symbol': option_symbol
                }
            else:
                # Execute options order via executor (with is_option=True)
                order = self.executor.execute_market_order(
                    symbol=option_symbol,
                    qty=contracts,
                    side='buy',
                    is_option=True
                )
            
            if order and order.get('status') == 'filled':
                filled_price = order.get('filled_avg_price', option_price)
                filled_qty = order.get('filled_qty', contracts)
                
                # Add to position tracking (use option symbol)
                self.positions[option_symbol] = {
                    'qty': filled_qty,
                    'entry_price': filled_price,
                    'side': 'long',  # Always 'long' because we're buying options
                    'agent_name': signal.get('agent', 'Unknown'),
                    'entry_time': datetime.now(),
                    'current_qty': filled_qty,
                    'underlying': symbol,
                    'expiration': target_expiration,
                    'option_type': option_type,  # 'call' for LONG, 'put' for SHORT
                    'instrument_type': 'option',
                    'signal_direction': signal['direction']  # Track original signal direction
                }
                
                # Add to profit manager
                self.profit_manager.add_position(
                    option_symbol, filled_qty, filled_price, 'long'
                )
                
                logger.info(f"✅ OPTIONS TRADE EXECUTED: {option_symbol} BUY {filled_qty} contracts @ ${filled_price:.2f}")
                logger.info(f"   Underlying: {symbol}")
                logger.info(f"   Option Type: {option_type.upper()} ({'CALL' if option_type == 'call' else 'PUT'})")
                logger.info(f"   Signal Direction: {signal['direction']}")
                logger.info(f"   Expiration: {target_expiration} (DTE: {(target_expiration - today).days})")
                logger.info(f"   Signal: {signal['source']} ({signal['agent']})")
                logger.info(f"   Confidence: {signal['confidence']:.2%}")
                
        except Exception as e:
            logger.error(f"Error executing options trade for {symbol}: {e}", exc_info=True)
    
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

