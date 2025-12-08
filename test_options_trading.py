#!/usr/bin/env python3
"""
Test Options Trading Mode - Real Paper Trading
- Options trading only
- 10% profit target / 5% stop loss
- Lower confidence threshold (0.30)
- Real execution (paper account)
- Bypasses some filters for testing
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime
from config import Config
from alpaca_client import AlpacaClient
from core.live.broker_executor import BrokerExecutor
from core.live.options_broker_client import OptionsBrokerClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.risk.profit_manager import ProfitManager
from core.risk.advanced_risk_manager import AdvancedRiskManager
from services.options_data_feed import OptionsDataFeed
from services.iv_calculator import IVCalculator
from core.agents.options_agent import OptionsAgent
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_options_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestOptionsTrader:
    """Test options trading with relaxed rules"""
    
    def __init__(self):
        """Initialize test trader"""
        logger.info("="*70)
        logger.info("TEST OPTIONS TRADING MODE - REAL PAPER TRADING")
        logger.info("="*70)
        logger.info("Settings:")
        logger.info("  - Asset Type: OPTIONS ONLY")
        logger.info("  - Profit Target: 10%")
        logger.info("  - Stop Loss: 5%")
        logger.info("  - Confidence Threshold: 0.30 (lowered for testing)")
        logger.info("  - Paper Trading: YES (real execution)")
        logger.info("  - Dry Run: NO")
        logger.info("="*70)
        
        # Initialize clients
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        self.executor = BrokerExecutor(self.client)
        self.options_client = OptionsBrokerClient(self.client)
        
        # Initialize options services
        self.options_feed = OptionsDataFeed(self.client)
        self.iv_calculator = IVCalculator()
        
        # Initialize options agent with lower confidence
        self.options_agent = OptionsAgent(self.options_feed, self.iv_calculator)
        self.options_agent.min_confidence = 0.30  # Lower threshold for testing
        
        # Initialize orchestrator (for regime classification)
        self.orchestrator = MultiAgentOrchestrator(self.client)
        
        # Profit manager with test settings
        self.profit_manager = ProfitManager(
            tp1_pct=0.10,  # 10% profit target
            tp1_exit_pct=1.00,  # Full exit at 10%
            tp2_pct=0.20,
            tp2_exit_pct=1.00,
            tp3_pct=0.30,
            tp3_exit_pct=1.00,
            tp4_pct=0.50,
            tp4_exit_pct=1.00,
            tp5_pct=1.00,
            tp5_exit_pct=1.00,
            stop_loss_pct=0.05,  # 5% stop loss
            trailing_stop_activation_pct=0.10,
            trailing_stop_min_profit_pct=0.05
        )
        
        # Risk manager (relaxed for testing)
        self.risk_manager = AdvancedRiskManager(
            initial_balance=Config.INITIAL_BALANCE,
            daily_loss_limit_pct=0.10,  # 10% max daily loss
            max_drawdown_pct=0.20,  # 20% max drawdown
            max_loss_streak=5  # Allow more losses for testing
        )
        
        # Track positions
        self.positions = {}
        
    def get_account_info(self):
        """Get account information"""
        try:
            account = self.client.get_account()
            logger.info(f"Account Status:")
            logger.info(f"  Equity: ${account['equity']:,.2f}")
            logger.info(f"  Cash: ${account['cash']:,.2f}")
            logger.info(f"  Buying Power: ${account['buying_power']:,.2f}")
            return account
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    def find_options_opportunity(self, symbol: str):
        """Find options trading opportunity for a symbol"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Scanning {symbol} for options opportunities...")
            logger.info(f"{'='*60}")
            
            # Get current price and features
            bars = self.client.get_historical_bars(
                symbol,
                '1Min',
                datetime.now().replace(hour=9, minute=30, second=0, microsecond=0),
                datetime.now()
            )
            
            if bars.empty:
                logger.warning(f"No bars available for {symbol}")
                return None
            
            current_price = float(bars['close'].iloc[-1])
            logger.info(f"Current {symbol} price: ${current_price:.2f}")
            
            # Get regime signal using orchestrator
            try:
                # Get bars for orchestrator
                bars = self.client.get_historical_bars(
                    symbol,
                    '1Min',
                    datetime.now().replace(hour=9, minute=30, second=0, microsecond=0),
                    datetime.now()
                )
                
                if bars.empty:
                    logger.warning(f"No bars for {symbol}")
                    return None
                
                # Analyze with orchestrator
                trade_intent = self.orchestrator.analyze_symbol(symbol, bars)
                
                # Get regime from orchestrator's internal state
                # We'll create a simple regime signal for testing
                from core.regime.classifier import RegimeSignal, RegimeType, Bias
                regime_signal = RegimeSignal(
                    regime_type=RegimeType.TREND,
                    confidence=0.60,
                    bias=Bias.BULLISH,
                    trend_direction='up',
                    volatility_level='medium'
                )
                
                # Calculate features
                from core.features.indicators import FeatureEngine
                feature_engine = FeatureEngine()
                features = feature_engine.calculate_all_features(bars)
                features['current_price'] = current_price
                
            except Exception as e:
                logger.warning(f"Error getting regime signal: {e}")
                # Create default regime for testing
                from core.regime.classifier import RegimeSignal, RegimeType, Bias
                regime_signal = RegimeSignal(
                    regime_type=RegimeType.TREND,
                    confidence=0.50,
                    bias=Bias.BULLISH,
                    trend_direction='up',
                    volatility_level='medium'
                )
                features = {'current_price': current_price}
            
            features['current_price'] = current_price
            
            # Check if options agent should activate
            if regime_signal and self.options_agent.should_activate(regime_signal, features):
                logger.info(f"✅ Options agent activated for {symbol}")
                logger.info(f"   Regime: {regime_signal.regime_type.value}")
                logger.info(f"   Bias: {regime_signal.bias.value}")
                logger.info(f"   Confidence: {regime_signal.confidence:.2f}")
                
                # Evaluate options trade
                trade_intent = self.options_agent.evaluate(symbol, regime_signal, features)
                
                if trade_intent:
                    logger.info(f"✅ Options trade signal generated!")
                    logger.info(f"   Direction: {trade_intent.direction.value}")
                    logger.info(f"   Confidence: {trade_intent.confidence:.2f}")
                    logger.info(f"   Option Symbol: {trade_intent.symbol}")  # symbol is the option symbol
                    logger.info(f"   Entry Price: ${trade_intent.entry_price:.2f}")
                    
                    # Calculate quantity based on position size
                    account = self.get_account_info()
                    if not account:
                        return None
                    
                    position_value = account['equity'] * trade_intent.position_size_suggestion
                    option_price = trade_intent.entry_price or 1.0
                    quantity = int(position_value / (option_price * 100))  # Options are per 100 shares
                    quantity = max(1, quantity)  # At least 1 contract
                    
                    return {
                        'symbol': symbol,
                        'option_symbol': trade_intent.symbol,  # This is the option contract symbol
                        'direction': trade_intent.direction.value,
                        'quantity': quantity,
                        'entry_price': trade_intent.entry_price or 1.0,
                        'confidence': trade_intent.confidence,
                        'reason': trade_intent.reasoning or f"Options Agent - {regime_signal.regime_type.value}"
                    }
                else:
                    logger.info(f"⏸️  Options agent evaluated but no trade signal")
            else:
                logger.info(f"⏸️  Options agent not activated (waiting for better conditions)")
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding options opportunity for {symbol}: {e}", exc_info=True)
            return None
    
    def execute_options_trade(self, signal: dict):
        """Execute an options trade"""
        try:
            symbol = signal['symbol']
            option_symbol = signal['option_symbol']
            direction = signal['direction']
            quantity = int(signal['quantity'])
            entry_price = signal['entry_price']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"EXECUTING OPTIONS TRADE")
            logger.info(f"{'='*60}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Option: {option_symbol}")
            logger.info(f"Direction: {direction}")
            logger.info(f"Quantity: {quantity} contracts")
            logger.info(f"Expected Entry: ${entry_price:.2f}")
            logger.info(f"{'='*60}")
            
            # Check risk
            account = self.get_account_info()
            if not account:
                logger.error("Cannot get account info - aborting trade")
                return False
            
            # Calculate position value
            position_value = entry_price * quantity * 100  # Options are per 100 shares
            max_position_value = account['equity'] * 0.10  # 10% max per position
            
            if position_value > max_position_value:
                logger.warning(f"Position size too large: ${position_value:,.2f} > ${max_position_value:,.2f}")
                # Reduce quantity
                quantity = int(max_position_value / (entry_price * 100))
                logger.info(f"Reduced quantity to {quantity} contracts")
            
            if quantity < 1:
                logger.warning("Quantity too small after risk check")
                return False
            
            # Execute order
            side = 'buy' if direction == 'LONG' else 'sell'
            
            logger.info(f"Placing {side} order for {quantity} {option_symbol} contracts...")
            
            order = self.options_client.place_option_order(
                option_symbol=option_symbol,
                qty=quantity,
                side=side,
                order_type='market'
            )
            
            if order and order.get('status') in ['filled', 'partially_filled']:
                filled_price = order.get('filled_avg_price', entry_price)
                filled_qty = order.get('filled_qty', quantity)
                
                logger.info(f"\n✅ OPTIONS TRADE EXECUTED!")
                logger.info(f"   Option: {option_symbol}")
                logger.info(f"   Side: {side}")
                logger.info(f"   Quantity: {filled_qty} contracts")
                logger.info(f"   Fill Price: ${filled_price:.2f}")
                logger.info(f"   Position Value: ${filled_price * filled_qty * 100:,.2f}")
                
                # Track position
                self.positions[option_symbol] = {
                    'symbol': symbol,
                    'option_symbol': option_symbol,
                    'qty': filled_qty,
                    'entry_price': filled_price,
                    'side': 'long' if side == 'buy' else 'short',
                    'entry_time': datetime.now(),
                    'current_qty': filled_qty
                }
                
                return True
            else:
                logger.warning(f"Order not filled: {order}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing options trade: {e}", exc_info=True)
            return False
    
    def monitor_positions(self):
        """Monitor and manage open positions"""
        if not self.positions:
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"MONITORING {len(self.positions)} POSITIONS")
        logger.info(f"{'='*60}")
        
        for option_symbol, position in list(self.positions.items()):
            try:
                # Get current position from broker
                pos = self.options_client.get_option_position(option_symbol)
                
                if not pos:
                    logger.warning(f"Position {option_symbol} not found - may be closed")
                    del self.positions[option_symbol]
                    continue
                
                entry_price = position['entry_price']
                current_price = pos['current_price']
                qty = pos['qty']
                pnl_pct = pos.get('unrealized_plpc', 0) * 100
                
                logger.info(f"{option_symbol}:")
                logger.info(f"  Entry: ${entry_price:.2f} | Current: ${current_price:.2f}")
                logger.info(f"  P&L: {pnl_pct:.2f}% | Qty: {qty}")
                
                # Check profit targets and stop loss
                if pnl_pct >= 10.0:  # 10% profit target
                    logger.info(f"  ✅ PROFIT TARGET HIT! Closing position...")
                    self.close_position(option_symbol, 'profit_target')
                elif pnl_pct <= -5.0:  # 5% stop loss
                    logger.info(f"  ⛔ STOP LOSS HIT! Closing position...")
                    self.close_position(option_symbol, 'stop_loss')
                    
            except Exception as e:
                logger.error(f"Error monitoring position {option_symbol}: {e}")
    
    def close_position(self, option_symbol: str, reason: str):
        """Close an options position"""
        try:
            position = self.positions.get(option_symbol)
            if not position:
                return
            
            side = position['side']
            qty = position['current_qty']
            close_side = 'sell' if side == 'long' else 'buy'
            
            logger.info(f"Closing {option_symbol}: {close_side} {qty} contracts (reason: {reason})")
            
            order = self.options_client.place_option_order(
                option_symbol=option_symbol,
                qty=int(qty),
                side=close_side,
                order_type='market'
            )
            
            if order and order.get('status') in ['filled', 'partially_filled']:
                logger.info(f"✅ Position closed: {option_symbol}")
                del self.positions[option_symbol]
            else:
                logger.warning(f"Failed to close position: {order}")
                
        except Exception as e:
            logger.error(f"Error closing position {option_symbol}: {e}")
    
    def run_trading_cycle(self):
        """Run one trading cycle"""
        logger.info(f"\n{'#'*70}")
        logger.info(f"TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'#'*70}")
        
        # Check account
        account = self.get_account_info()
        if not account:
            logger.error("Cannot get account - skipping cycle")
            return
        
        # Monitor existing positions
        self.monitor_positions()
        
        # Check if we can open new positions
        max_positions = 5  # Limit for testing
        if len(self.positions) >= max_positions:
            logger.info(f"Max positions reached ({len(self.positions)}/{max_positions})")
            return
        
        # Scan for opportunities
        logger.info(f"\nScanning for options opportunities...")
        opportunities = []
        
        for ticker in Config.TICKERS[:3]:  # Test with first 3 tickers
            signal = self.find_options_opportunity(ticker)
            if signal and signal['confidence'] >= 0.30:  # Lower threshold
                opportunities.append(signal)
        
        # Execute best opportunity
        if opportunities:
            # Sort by confidence
            opportunities.sort(key=lambda x: x['confidence'], reverse=True)
            best = opportunities[0]
            
            logger.info(f"\n🎯 Best opportunity: {best['symbol']} (confidence: {best['confidence']:.2f})")
            
            # Execute trade
            if self.execute_options_trade(best):
                logger.info("✅ Trade executed successfully!")
            else:
                logger.warning("❌ Trade execution failed")
        else:
            logger.info("⏸️  No opportunities found this cycle")
    
    def run(self):
        """Main trading loop"""
        logger.info("\n🚀 Starting Test Options Trading...")
        logger.info("Press CTRL+C to stop\n")
        
        try:
            cycle_count = 0
            while True:
                cycle_count += 1
                self.run_trading_cycle()
                
                # Wait 3 minutes between cycles
                logger.info(f"\nWaiting 3 minutes until next cycle...")
                time.sleep(180)
                
        except KeyboardInterrupt:
            logger.info("\n\n⛔ Trading stopped by user")
            logger.info("Closing all positions...")
            
            # Close all positions
            for option_symbol in list(self.positions.keys()):
                self.close_position(option_symbol, 'manual_close')
            
            logger.info("✅ All positions closed. Exiting.")

if __name__ == "__main__":
    trader = TestOptionsTrader()
    trader.run()

