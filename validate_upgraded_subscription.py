#!/usr/bin/env python3
"""
Validate Upgraded Alpaca Subscription
Comprehensive test of data access, signal generation, and trading capability
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/validate_subscription.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SubscriptionValidator:
    """Validate upgraded Alpaca subscription"""
    
    def __init__(self):
        logger.info("="*70)
        logger.info("VALIDATING UPGRADED ALPACA SUBSCRIPTION")
        logger.info("="*70)
        
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        self.orchestrator = MultiAgentOrchestrator(self.client)
        self.trader = IntegratedTrader(dry_run=False, paper_trading=True)
        
        self.results = {
            'data_access': {'passed': 0, 'failed': 0, 'details': []},
            'signal_generation': {'passed': 0, 'failed': 0, 'details': []},
            'trading_capability': {'passed': 0, 'failed': 0, 'details': []}
        }
    
    def test_data_access(self):
        """Test 1: Historical Data Access"""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: HISTORICAL DATA ACCESS")
        logger.info("="*70)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        success_count = 0
        fail_count = 0
        
        for ticker in Config.TICKERS:
            try:
                logger.info(f"\nTesting {ticker}...")
                bars = self.client.get_historical_bars(
                    ticker,
                    TimeFrame.Day,
                    start_date,
                    end_date
                )
                
                if bars.empty:
                    logger.warning(f"  ❌ {ticker}: No data returned")
                    fail_count += 1
                    self.results['data_access']['details'].append(
                        f"{ticker}: No data"
                    )
                elif len(bars) < 50:
                    logger.warning(f"  ⚠️  {ticker}: Insufficient data ({len(bars)} bars, need 50+)")
                    fail_count += 1
                    self.results['data_access']['details'].append(
                        f"{ticker}: Only {len(bars)} bars"
                    )
                else:
                    logger.info(f"  ✅ {ticker}: {len(bars)} bars retrieved successfully")
                    success_count += 1
                    self.results['data_access']['details'].append(
                        f"{ticker}: ✅ {len(bars)} bars"
                    )
                    
            except Exception as e:
                error_msg = str(e)
                if "subscription does not permit" in error_msg.lower():
                    logger.error(f"  ❌ {ticker}: Subscription limitation - {error_msg[:60]}")
                else:
                    logger.error(f"  ❌ {ticker}: Error - {error_msg[:60]}")
                fail_count += 1
                self.results['data_access']['details'].append(
                    f"{ticker}: ❌ {error_msg[:40]}"
                )
        
        self.results['data_access']['passed'] = success_count
        self.results['data_access']['failed'] = fail_count
        
        logger.info(f"\n📊 Data Access Results: {success_count}/{len(Config.TICKERS)} tickers successful")
        
        if success_count == len(Config.TICKERS):
            logger.info("✅ ALL TICKERS CAN ACCESS HISTORICAL DATA!")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️  Partial success: {success_count}/{len(Config.TICKERS)} tickers working")
            return True  # Partial success is acceptable
        else:
            logger.error("❌ NO TICKERS CAN ACCESS HISTORICAL DATA - Subscription may not be upgraded")
            return False
    
    def test_signal_generation(self):
        """Test 2: Signal Generation"""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: SIGNAL GENERATION")
        logger.info("="*70)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        signals_found = 0
        signals_above_threshold = 0
        tested_count = 0
        
        for ticker in Config.TICKERS[:5]:  # Test first 5 to save time
            try:
                logger.info(f"\nTesting {ticker}...")
                bars = self.client.get_historical_bars(
                    ticker,
                    TimeFrame.Day,
                    start_date,
                    end_date
                )
                
                if bars.empty or len(bars) < 50:
                    logger.warning(f"  ⚠️  {ticker}: Skipping (insufficient data)")
                    continue
                
                tested_count += 1
                
                # Test orchestrator
                intent = self.orchestrator.analyze_symbol(ticker, bars)
                
                if intent:
                    signals_found += 1
                    logger.info(f"  ✅ {ticker}: Signal generated")
                    logger.info(f"     Direction: {intent.direction.value}")
                    logger.info(f"     Confidence: {intent.confidence:.2%}")
                    logger.info(f"     Agent: {intent.agent_name}")
                    
                    if intent.confidence >= 0.5:
                        signals_above_threshold += 1
                        logger.info(f"     ✅ Confidence >= 50% (would execute)")
                        self.results['signal_generation']['details'].append(
                            f"{ticker}: ✅ {intent.direction.value} @ {intent.confidence:.2%} (executable)"
                        )
                    else:
                        logger.info(f"     ⏸️  Confidence {intent.confidence:.2%} < 50% (below threshold)")
                        self.results['signal_generation']['details'].append(
                            f"{ticker}: ⏸️  {intent.direction.value} @ {intent.confidence:.2%} (low confidence)"
                        )
                else:
                    logger.info(f"  ⏸️  {ticker}: No signal generated (waiting for better conditions)")
                    self.results['signal_generation']['details'].append(
                        f"{ticker}: ⏸️  No signal"
                    )
                    
            except Exception as e:
                logger.error(f"  ❌ {ticker}: Error - {e}")
                self.results['signal_generation']['details'].append(
                    f"{ticker}: ❌ Error"
                )
        
        self.results['signal_generation']['passed'] = signals_above_threshold
        self.results['signal_generation']['failed'] = tested_count - signals_above_threshold
        
        logger.info(f"\n📊 Signal Generation Results:")
        logger.info(f"   Tickers tested: {tested_count}")
        logger.info(f"   Signals generated: {signals_found}")
        logger.info(f"   Signals >= 50% confidence: {signals_above_threshold}")
        
        if signals_found > 0:
            logger.info("✅ SIGNAL GENERATION IS WORKING!")
            return True
        else:
            logger.warning("⚠️  No signals generated (may need better market conditions)")
            return True  # System is working, just no good setups
    
    def test_trading_capability(self):
        """Test 3: Trading Capability"""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: TRADING CAPABILITY")
        logger.info("="*70)
        
        try:
            # Test account access
            account = self.client.get_account()
            logger.info(f"✅ Account accessible")
            logger.info(f"   Equity: ${account['equity']:,.2f}")
            logger.info(f"   Buying Power: ${account['buying_power']:,.2f}")
            logger.info(f"   Trading Blocked: {account.get('trading_blocked', False)}")
            
            if account.get('trading_blocked', False):
                logger.error("❌ Trading is blocked on account")
                return False
            
            # Test risk manager
            risk_status = self.trader.risk_manager.get_risk_status()
            logger.info(f"✅ Risk manager active")
            logger.info(f"   Risk Level: {risk_status['risk_level']}")
            logger.info(f"   Daily P&L: ${risk_status.get('daily_pnl', 0):.2f}")
            
            # Test market status
            is_open = self.client.is_market_open()
            logger.info(f"✅ Market status check working")
            logger.info(f"   Market Open: {is_open}")
            
            # Test position access
            positions = self.client.get_positions()
            logger.info(f"✅ Position access working")
            logger.info(f"   Current Positions: {len(positions)}")
            
            self.results['trading_capability']['passed'] = 4
            self.results['trading_capability']['details'] = [
                "Account accessible",
                "Risk manager active",
                "Market status check working",
                "Position access working"
            ]
            
            logger.info("\n✅ ALL TRADING CAPABILITIES WORKING!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Trading capability test failed: {e}")
            self.results['trading_capability']['failed'] = 1
            return False
    
    def generate_report(self):
        """Generate final validation report"""
        logger.info("\n" + "="*70)
        logger.info("VALIDATION REPORT")
        logger.info("="*70)
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        
        logger.info(f"\n📊 OVERALL RESULTS:")
        logger.info(f"   Total Tests Passed: {total_passed}")
        logger.info(f"   Total Tests Failed: {total_failed}")
        
        logger.info(f"\n📋 DETAILED RESULTS:")
        
        # Data Access
        data_passed = self.results['data_access']['passed']
        data_total = data_passed + self.results['data_access']['failed']
        logger.info(f"\n1. DATA ACCESS: {data_passed}/{data_total} tickers")
        for detail in self.results['data_access']['details'][:5]:
            logger.info(f"   {detail}")
        if len(self.results['data_access']['details']) > 5:
            logger.info(f"   ... and {len(self.results['data_access']['details']) - 5} more")
        
        # Signal Generation
        sig_passed = self.results['signal_generation']['passed']
        sig_total = sig_passed + self.results['signal_generation']['failed']
        logger.info(f"\n2. SIGNAL GENERATION: {sig_passed} executable signals found")
        for detail in self.results['signal_generation']['details']:
            logger.info(f"   {detail}")
        
        # Trading Capability
        trade_passed = self.results['trading_capability']['passed']
        logger.info(f"\n3. TRADING CAPABILITY: {trade_passed}/4 components")
        for detail in self.results['trading_capability']['details']:
            logger.info(f"   ✅ {detail}")
        
        logger.info("\n" + "="*70)
        
        # Final verdict
        if data_passed > 0 and trade_passed == 4:
            logger.info("✅ SUBSCRIPTION UPGRADE VALIDATED - SYSTEM READY FOR TRADING!")
            logger.info("\n🎯 Next Steps:")
            logger.info("   1. System will now scan all tickers every 5 minutes")
            logger.info("   2. When signals >= 50% confidence are found, trades will execute")
            logger.info("   3. Monitor logs/tradenova_daemon.log for activity")
            logger.info("   4. Check dashboard for positions and P/L")
        elif data_passed > 0:
            logger.warning("⚠️  PARTIAL VALIDATION - Some components need attention")
        else:
            logger.error("❌ VALIDATION FAILED - Subscription may not be fully upgraded")
            logger.error("   Check Alpaca dashboard for subscription status")
        
        logger.info("="*70)
    
    def run_all_tests(self):
        """Run complete validation"""
        try:
            # Test 1: Data Access
            data_ok = self.test_data_access()
            
            # Test 2: Signal Generation (only if data works)
            if data_ok:
                self.test_signal_generation()
            
            # Test 3: Trading Capability
            self.test_trading_capability()
            
            # Generate report
            self.generate_report()
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}", exc_info=True)

def main():
    validator = SubscriptionValidator()
    validator.run_all_tests()

if __name__ == "__main__":
    main()

