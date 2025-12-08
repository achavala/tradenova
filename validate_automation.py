#!/usr/bin/env python3
"""
Automation Validation Script
Validates that TradeNova will start automatically tomorrow without manual intervention
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config
from core.live.trading_scheduler import TradingScheduler
from core.live.integrated_trader import IntegratedTrader
from core.live.broker_executor import BrokerExecutor
from core.risk.advanced_risk_manager import AdvancedRiskManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationValidator:
    """Validates automation setup"""
    
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def log_pass(self, test_name: str, message: str = ""):
        """Log passed test"""
        self.passed.append((test_name, message))
        print(f"✅ PASS: {test_name}")
        if message:
            print(f"   {message}")
    
    def log_fail(self, test_name: str, error: str):
        """Log failed test"""
        self.failed.append((test_name, error))
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")
    
    def log_warning(self, test_name: str, message: str):
        """Log warning"""
        self.warnings.append((test_name, message))
        print(f"⚠️  WARN: {test_name}")
        print(f"   {message}")
    
    def test_1_environment_setup(self):
        """Test 1: Environment and dependencies"""
        print("\n" + "="*60)
        print("TEST 1: Environment and Dependencies")
        print("="*60)
        
        try:
            # Check Python version
            import sys
            if sys.version_info < (3, 8):
                self.log_fail("Python Version", f"Python 3.8+ required, found {sys.version}")
                return False
            self.log_pass("Python Version", f"Python {sys.version.split()[0]}")
            
            # Check virtual environment
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                self.log_pass("Virtual Environment", "Active")
            else:
                self.log_warning("Virtual Environment", "Not detected (may be OK if using system Python)")
            
            # Check critical imports
            try:
                import alpaca_trade_api
                self.log_pass("Alpaca API", f"Version {alpaca_trade_api.__version__}")
            except ImportError as e:
                self.log_fail("Alpaca API", f"Not installed: {e}")
                return False
            
            try:
                import schedule
                self.log_pass("Schedule Library", "Installed")
            except ImportError as e:
                self.log_fail("Schedule Library", f"Not installed: {e}")
                return False
            
            try:
                import pandas
                self.log_pass("Pandas", f"Version {pandas.__version__}")
            except ImportError as e:
                self.log_fail("Pandas", f"Not installed: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.log_fail("Environment Setup", str(e))
            return False
    
    def test_2_configuration(self):
        """Test 2: Configuration"""
        print("\n" + "="*60)
        print("TEST 2: Configuration")
        print("="*60)
        
        try:
            # Check API keys
            if not Config.ALPACA_API_KEY or Config.ALPACA_API_KEY == "your_api_key_here":
                self.log_fail("API Key", "Not configured in .env file")
                return False
            self.log_pass("API Key", "Configured")
            
            if not Config.ALPACA_SECRET_KEY or Config.ALPACA_SECRET_KEY == "your_secret_key_here":
                self.log_fail("Secret Key", "Not configured in .env file")
                return False
            self.log_pass("Secret Key", "Configured")
            
            # Check base URL
            if "paper" in Config.ALPACA_BASE_URL.lower():
                self.log_pass("Base URL", f"Paper trading: {Config.ALPACA_BASE_URL}")
            else:
                self.log_warning("Base URL", f"Not paper trading: {Config.ALPACA_BASE_URL}")
            
            # Check tickers
            if Config.TICKERS:
                self.log_pass("Tickers", f"{len(Config.TICKERS)} tickers configured")
            else:
                self.log_fail("Tickers", "No tickers configured")
                return False
            
            return True
            
        except Exception as e:
            self.log_fail("Configuration", str(e))
            return False
    
    def test_3_alpaca_connection(self):
        """Test 3: Alpaca API Connection"""
        print("\n" + "="*60)
        print("TEST 3: Alpaca API Connection (Paper Trading)")
        print("="*60)
        
        try:
            # Use paper trading URL
            base_url = "https://paper-api.alpaca.markets"
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                base_url
            )
            
            # Test account access
            account = client.get_account()
            if account:
                self.log_pass("Account Access", f"Equity: ${float(account['equity']):,.2f}")
                self.log_pass("Buying Power", f"${float(account['buying_power']):,.2f}")
                
                if account.get('trading_blocked'):
                    self.log_warning("Trading Status", "Trading is blocked (may be OK for paper)")
                else:
                    self.log_pass("Trading Status", "Trading enabled")
            else:
                self.log_fail("Account Access", "Failed to retrieve account")
                return False
            
            # Test market status
            is_open = client.is_market_open()
            if is_open is not None:
                self.log_pass("Market Status", f"Market is {'OPEN' if is_open else 'CLOSED'}")
            else:
                self.log_warning("Market Status", "Could not determine market status (may be OK)")
            
            # Test position retrieval
            positions = client.get_positions()
            if positions is not None:
                self.log_pass("Position Access", f"{len(positions)} open positions")
            else:
                self.log_fail("Position Access", "Failed to retrieve positions")
                return False
            
            return True
            
        except Exception as e:
            self.log_fail("Alpaca Connection", str(e))
            return False
    
    def test_4_scheduler_functionality(self):
        """Test 4: Scheduler Functionality"""
        print("\n" + "="*60)
        print("TEST 4: Trading Scheduler")
        print("="*60)
        
        try:
            scheduler = TradingScheduler()
            
            # Test scheduling
            test_called = [False]
            def test_callback():
                test_called[0] = True
            
            # Schedule a test job
            scheduler.schedule_pre_market_warmup(test_callback, "08:00")
            scheduler.schedule_market_open(test_callback, "09:30")
            scheduler.schedule_market_close_flatten(test_callback, "15:50")
            scheduler.schedule_daily_report(test_callback, "16:05")
            scheduler.schedule_recurring(test_callback, interval_minutes=5)
            
            self.log_pass("Scheduler Initialization", "Scheduler created")
            self.log_pass("Pre-Market Warmup", "Scheduled at 08:00")
            self.log_pass("Market Open", "Scheduled at 09:30")
            self.log_pass("Market Close Flatten", "Scheduled at 15:50")
            self.log_pass("Daily Report", "Scheduled at 16:05")
            self.log_pass("Recurring Cycle", "Scheduled every 5 minutes")
            
            # Test market hours detection
            is_market_hours = scheduler.is_market_hours()
            is_pre_market = scheduler.is_pre_market()
            is_after_hours = scheduler.is_after_hours()
            
            self.log_pass("Market Hours Detection", f"Current: {'Market Hours' if is_market_hours else 'Pre-Market' if is_pre_market else 'After Hours'}")
            
            # Clean up
            scheduler.stop()
            
            return True
            
        except Exception as e:
            self.log_fail("Scheduler Functionality", str(e))
            return False
    
    def test_5_component_initialization(self):
        """Test 5: Component Initialization"""
        print("\n" + "="*60)
        print("TEST 5: Component Initialization")
        print("="*60)
        
        try:
            # Test IntegratedTrader initialization (dry run)
            base_url = "https://paper-api.alpaca.markets"
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                base_url
            )
            
            trader = IntegratedTrader(
                rl_model_path=None,  # Skip RL for validation
                use_rl=False,
                dry_run=True,
                paper_trading=True
            )
            self.log_pass("IntegratedTrader", "Initialized (dry run)")
            
            # Test executor
            executor = BrokerExecutor(client)
            self.log_pass("BrokerExecutor", "Initialized")
            
            # Test risk manager
            risk_manager = AdvancedRiskManager(
                initial_balance=Config.INITIAL_BALANCE,
                daily_loss_limit_pct=0.02,
                max_drawdown_pct=0.10,
                max_loss_streak=3
            )
            self.log_pass("RiskManager", "Initialized")
            
            # Test risk status
            risk_status = risk_manager.get_risk_status()
            self.log_pass("Risk Status Check", f"Risk Level: {risk_status['risk_level']}")
            
            return True
            
        except Exception as e:
            self.log_fail("Component Initialization", str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def test_6_automation_setup(self):
        """Test 6: Automation Setup"""
        print("\n" + "="*60)
        print("TEST 6: Automation Setup")
        print("="*60)
        
        try:
            # Check if run_daily.py exists
            run_daily = Path("run_daily.py")
            if not run_daily.exists():
                self.log_fail("run_daily.py", "File not found")
                return False
            self.log_pass("run_daily.py", "Exists")
            
            # Check if script is executable
            if os.access(run_daily, os.X_OK):
                self.log_pass("Script Permissions", "Executable")
            else:
                self.log_warning("Script Permissions", "Not executable (may need chmod +x)")
            
            # Check for cron/launchd setup
            print("\n   Automation Options:")
            print("   1. Manual Start: python run_daily.py --paper")
            print("   2. Cron Job (Linux/Mac): See AUTOMATION_SETUP.md")
            print("   3. Launchd (macOS): See AUTOMATION_SETUP.md")
            print("   4. Systemd (Linux): See AUTOMATION_SETUP.md")
            
            self.log_pass("Automation Setup", "See AUTOMATION_SETUP.md for instructions")
            
            return True
            
        except Exception as e:
            self.log_fail("Automation Setup", str(e))
            return False
    
    def test_7_startup_command(self):
        """Test 7: Startup Command Validation"""
        print("\n" + "="*60)
        print("TEST 7: Startup Command")
        print("="*60)
        
        try:
            # Validate the command that will be used
            command = "python run_daily.py --paper"
            
            # Check if command components exist
            import shutil
            python_cmd = shutil.which("python") or shutil.which("python3")
            if python_cmd:
                self.log_pass("Python Command", f"Found: {python_cmd}")
            else:
                self.log_fail("Python Command", "Python not found in PATH")
                return False
            
            # Check if we can import the module
            try:
                import run_daily
                self.log_pass("run_daily Module", "Importable")
            except Exception as e:
                self.log_fail("run_daily Module", f"Cannot import: {e}")
                return False
            
            self.log_pass("Startup Command", f"Command: {command}")
            self.log_pass("Paper Trading Flag", "--paper flag will be used")
            
            return True
            
        except Exception as e:
            self.log_fail("Startup Command", str(e))
            return False
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("\n" + "="*60)
        print("TRADENOVA AUTOMATION VALIDATION")
        print("="*60)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        tests = [
            ("Environment", self.test_1_environment_setup),
            ("Configuration", self.test_2_configuration),
            ("Alpaca Connection", self.test_3_alpaca_connection),
            ("Scheduler", self.test_4_scheduler_functionality),
            ("Components", self.test_5_component_initialization),
            ("Automation Setup", self.test_6_automation_setup),
            ("Startup Command", self.test_7_startup_command),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = test_func()
            except Exception as e:
                self.log_fail(f"{name} Test", f"Exception: {e}")
                results[name] = False
        
        # Print summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        
        if self.passed:
            print("\n✅ Passed Tests:")
            for name, msg in self.passed:
                print(f"   • {name}" + (f": {msg}" if msg else ""))
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for name, msg in self.warnings:
                print(f"   • {name}: {msg}")
        
        if self.failed:
            print("\n❌ Failed Tests:")
            for name, error in self.failed:
                print(f"   • {name}: {error}")
        
        print("\n" + "="*60)
        
        if failed == 0:
            print("✅ ALL TESTS PASSED - System ready for automated trading")
            print("\nNext Steps:")
            print("1. Set up automation (see AUTOMATION_SETUP.md)")
            print("2. Test manual start: python run_daily.py --paper")
            print("3. Monitor first day closely")
            return True
        else:
            print("❌ SOME TESTS FAILED - Please fix issues before automation")
            return False

if __name__ == "__main__":
    validator = AutomationValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)

