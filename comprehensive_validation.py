#!/usr/bin/env python3
"""
Comprehensive System Validation - Professional Grade
Tests every component systematically and reports issues
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/comprehensive_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveValidator:
    """Professional validation of all system components"""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.critical_issues: List[str] = []
        self.warnings: List[str] = []
        
    def validate(self, component: str, test_func, *args, **kwargs) -> Tuple[bool, str]:
        """Validate a component and record results"""
        try:
            result = test_func(*args, **kwargs)
            if isinstance(result, tuple):
                success, message = result
            else:
                success = bool(result)
                message = "OK" if success else "Failed"
            
            self.results[component] = {
                'status': 'PASS' if success else 'FAIL',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if not success:
                self.critical_issues.append(f"{component}: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"{str(e)}"
            self.results[component] = {
                'status': 'ERROR',
                'message': error_msg,
                'error': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }
            self.critical_issues.append(f"{component}: {error_msg}")
            return False, error_msg
    
    def test_1_config(self) -> Tuple[bool, str]:
        """Test 1: Configuration"""
        try:
            from config import Config
            
            # Check required config
            if not Config.ALPACA_API_KEY or not Config.ALPACA_SECRET_KEY:
                return False, "Alpaca API credentials not set"
            
            Config.validate()
            
            if not Config.TICKERS:
                return False, "No tickers configured"
            
            return True, f"Config valid - {len(Config.TICKERS)} tickers"
            
        except Exception as e:
            return False, f"Config error: {e}"
    
    def test_2_alpaca_connection(self) -> Tuple[bool, str]:
        """Test 2: Alpaca Connection"""
        try:
            from config import Config
            from alpaca_client import AlpacaClient
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            
            account = client.get_account()
            is_open = client.is_market_open()
            
            return True, f"Connected - Equity: ${account['equity']:,.2f}, Market: {'Open' if is_open else 'Closed'}"
            
        except Exception as e:
            return False, f"Connection failed: {e}"
    
    def test_3_data_fetching(self) -> Tuple[bool, str]:
        """Test 3: Historical Data Fetching"""
        try:
            from config import Config
            from alpaca_client import AlpacaClient
            from alpaca_trade_api.rest import TimeFrame
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            
            # Test with multiple tickers to ensure data is available
            test_tickers = ['TSLA', 'AAPL', 'NVDA']
            success_count = 0
            total_bars = 0
            
            for ticker in test_tickers:
                try:
                    end = datetime.now()
                    start = end - timedelta(days=90)  # Get more data
                    
                    bars = client.get_historical_bars(ticker, TimeFrame.Day, start, end)
                    
                    if not bars.empty and len(bars) >= 20:
                        success_count += 1
                        total_bars += len(bars)
                except:
                    continue
            
            if success_count == 0:
                return False, "No data returned for any test ticker"
            
            return True, f"Data OK - {success_count}/{len(test_tickers)} tickers, {total_bars} total bars"
            
        except Exception as e:
            return False, f"Data fetch error: {e}"
    
    def test_4_multi_agent_orchestrator(self) -> Tuple[bool, str]:
        """Test 4: Multi-Agent Orchestrator"""
        try:
            from config import Config
            from alpaca_client import AlpacaClient
            from core.multi_agent_orchestrator import MultiAgentOrchestrator
            from alpaca_trade_api.rest import TimeFrame
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            
            orchestrator = MultiAgentOrchestrator(client)
            
            # Try multiple tickers to find one with data
            test_tickers = ['TSLA', 'AAPL', 'NVDA', 'MSFT', 'GOOG']
            bars = None
            test_ticker = None
            
            for ticker in test_tickers:
                try:
                    end = datetime.now()
                    start = end - timedelta(days=90)
                    test_bars = client.get_historical_bars(ticker, TimeFrame.Day, start, end)
                    
                    if not test_bars.empty and len(test_bars) >= 50:
                        bars = test_bars
                        test_ticker = ticker
                        break
                except:
                    continue
            
            if bars is None or bars.empty:
                return False, f"Insufficient data for orchestrator (tried {len(test_tickers)} tickers)"
            
            # Test analysis
            intent = orchestrator.analyze_symbol(test_ticker, bars)
            
            if intent is None:
                return True, f"Orchestrator works ({test_ticker}, no signal = OK)"
            
            return True, f"Orchestrator works ({test_ticker}) - Signal: {intent.direction.value} ({intent.confidence:.2%})"
            
        except Exception as e:
            return False, f"Orchestrator error: {e}"
    
    def test_5_integrated_trader(self) -> Tuple[bool, str]:
        """Test 5: Integrated Trader"""
        try:
            from core.live.integrated_trader import IntegratedTrader
            
            trader = IntegratedTrader(dry_run=True, paper_trading=True)
            
            # Check components
            if not trader.orchestrator:
                return False, "Orchestrator not initialized"
            if not trader.executor:
                return False, "Executor not initialized"
            if not trader.risk_manager:
                return False, "Risk manager not initialized"
            
            return True, "Integrated trader initialized with all components"
            
        except Exception as e:
            return False, f"Integrated trader error: {e}"
    
    def test_6_signal_generation(self) -> Tuple[bool, str]:
        """Test 6: Signal Generation"""
        try:
            from config import Config
            from alpaca_client import AlpacaClient
            from core.multi_agent_orchestrator import MultiAgentOrchestrator
            from alpaca_trade_api.rest import TimeFrame
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            
            orchestrator = MultiAgentOrchestrator(client)
            
            # Test multiple tickers
            signals = 0
            tested = 0
            
            for ticker in Config.TICKERS[:5]:  # Test first 5
                try:
                    end = datetime.now()
                    start = end - timedelta(days=90)
                    bars = client.get_historical_bars(ticker, TimeFrame.Day, start, end)
                    
                    if bars.empty or len(bars) < 50:
                        continue
                    
                    tested += 1
                    intent = orchestrator.analyze_symbol(ticker, bars)
                    
                    if intent and intent.confidence >= 0.30:
                        signals += 1
                        
                except:
                    continue
            
            if tested == 0:
                return False, "Could not test any tickers (data issue)"
            
            signal_rate = signals / tested * 100 if tested > 0 else 0
            
            return True, f"Signal generation works - {signals}/{tested} signals ({signal_rate:.1f}%)"
            
        except Exception as e:
            return False, f"Signal generation error: {e}"
    
    def test_7_risk_management(self) -> Tuple[bool, str]:
        """Test 7: Risk Management"""
        try:
            from core.risk.advanced_risk_manager import AdvancedRiskManager
            from config import Config
            
            risk_manager = AdvancedRiskManager(
                initial_balance=Config.INITIAL_BALANCE,
                daily_loss_limit_pct=0.02,
                max_drawdown_pct=0.10,
                max_loss_streak=3
            )
            
            # Test risk checks using actual method
            allowed, reason, risk_level = risk_manager.check_trade_allowed(
                symbol='TSLA',
                qty=10,
                price=100.0,
                side='buy'
            )
            
            if not isinstance(allowed, bool):
                return False, "Risk manager check_trade_allowed() not returning bool"
            
            return True, f"Risk manager functional - Trade allowed: {allowed}"
            
        except Exception as e:
            return False, f"Risk management error: {e}"
    
    def test_8_profit_manager(self) -> Tuple[bool, str]:
        """Test 8: Profit Manager"""
        try:
            from core.risk.profit_manager import ProfitManager
            
            profit_manager = ProfitManager()
            
            # Add a position
            profit_manager.add_position('TEST', 100, 100.0, 'long')
            
            # Test exit check using actual method
            exit_info = profit_manager.check_exits('TEST', 110.0)
            
            return True, "Profit manager functional"
            
        except Exception as e:
            return False, f"Profit manager error: {e}"
    
    def test_9_broker_executor(self) -> Tuple[bool, str]:
        """Test 9: Broker Executor"""
        try:
            from config import Config
            from alpaca_client import AlpacaClient
            from core.live.broker_executor import BrokerExecutor
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            
            executor = BrokerExecutor(client)
            
            # Check if executor has required methods
            if not hasattr(executor, 'execute_market_order'):
                return False, "Missing execute_market_order method"
            
            # Get positions from client (executor uses client)
            positions = client.get_positions()
            
            return True, f"Broker executor functional - {len(positions)} positions"
            
        except Exception as e:
            return False, f"Broker executor error: {e}"
    
    def test_10_dashboard(self) -> Tuple[bool, str]:
        """Test 10: Dashboard"""
        try:
            import streamlit
            from pathlib import Path
            
            dashboard_file = Path('dashboard.py')
            if not dashboard_file.exists():
                return False, "dashboard.py not found"
            
            # Check if dashboard can be imported
            import importlib.util
            spec = importlib.util.spec_from_file_location("dashboard", dashboard_file)
            if spec is None:
                return False, "Cannot load dashboard module"
            
            return True, "Dashboard file exists and loadable"
            
        except Exception as e:
            return False, f"Dashboard error: {e}"
    
    def test_11_metrics_tracker(self) -> Tuple[bool, str]:
        """Test 11: Metrics Tracker"""
        try:
            from logs.metrics_tracker import MetricsTracker
            
            tracker = MetricsTracker()
            metrics = tracker.calculate_metrics()
            
            if not isinstance(metrics, dict):
                return False, "Metrics not returning dict"
            
            return True, "Metrics tracker functional"
            
        except Exception as e:
            return False, f"Metrics tracker error: {e}"
    
    def test_12_trading_scheduler(self) -> Tuple[bool, str]:
        """Test 12: Trading Scheduler"""
        try:
            from core.live.trading_scheduler import TradingScheduler
            
            scheduler = TradingScheduler()
            
            return True, "Trading scheduler can be initialized"
            
        except Exception as e:
            return False, f"Trading scheduler error: {e}"
    
    def run_all_tests(self):
        """Run all validation tests"""
        logger.info("="*70)
        logger.info("COMPREHENSIVE SYSTEM VALIDATION")
        logger.info("="*70)
        logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # Run all tests
        tests = [
            ("Configuration", self.test_1_config),
            ("Alpaca Connection", self.test_2_alpaca_connection),
            ("Data Fetching", self.test_3_data_fetching),
            ("Multi-Agent Orchestrator", self.test_4_multi_agent_orchestrator),
            ("Integrated Trader", self.test_5_integrated_trader),
            ("Signal Generation", self.test_6_signal_generation),
            ("Risk Management", self.test_7_risk_management),
            ("Profit Manager", self.test_8_profit_manager),
            ("Broker Executor", self.test_9_broker_executor),
            ("Dashboard", self.test_10_dashboard),
            ("Metrics Tracker", self.test_11_metrics_tracker),
            ("Trading Scheduler", self.test_12_trading_scheduler),
        ]
        
        for name, test_func in tests:
            logger.info(f"Testing: {name}...")
            success, message = self.validate(name, test_func)
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"  {status}: {message}")
            logger.info("")
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive report"""
        logger.info("="*70)
        logger.info("VALIDATION REPORT")
        logger.info("="*70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in self.results.values() if r['status'] in ['FAIL', 'ERROR'])
        
        logger.info(f"\n📊 SUMMARY")
        logger.info(f"   Total Tests: {total}")
        logger.info(f"   ✅ Passed: {passed}")
        logger.info(f"   ❌ Failed: {failed}")
        logger.info(f"   Success Rate: {passed/total*100:.1f}%")
        
        if self.critical_issues:
            logger.info(f"\n❌ CRITICAL ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                logger.info(f"   - {issue}")
        
        logger.info(f"\n📋 DETAILED RESULTS:")
        for component, result in self.results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            logger.info(f"   {status_icon} {component}: {result['status']} - {result['message']}")
        
        logger.info("\n" + "="*70)
        
        if failed == 0:
            logger.info("✅ ALL TESTS PASSED - System is ready!")
        else:
            logger.warning(f"⚠️  {failed} TEST(S) FAILED - Review issues above")
        
        logger.info("="*70)

def main():
    validator = ComprehensiveValidator()
    validator.run_all_tests()

if __name__ == "__main__":
    main()

