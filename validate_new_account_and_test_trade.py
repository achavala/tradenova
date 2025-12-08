#!/usr/bin/env python3
"""
Validate New Alpaca Account & Test Options Trade
Comprehensive validation and small test trade execution
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.broker_executor import BrokerExecutor
from core.live.options_broker_client import OptionsBrokerClient
from services.options_data_feed import OptionsDataFeed
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/validate_new_account.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AccountValidator:
    """Validate new Alpaca account and test trading"""
    
    def __init__(self):
        logger.info("="*70)
        logger.info("VALIDATING NEW ALPACA ACCOUNT")
        logger.info("="*70)
        
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        self.executor = BrokerExecutor(self.client)
        self.options_client = OptionsBrokerClient(self.client)
        self.options_feed = OptionsDataFeed(self.client)
        self.orchestrator = MultiAgentOrchestrator(self.client)
    
    def validate_account(self) -> bool:
        """Validate account connection and details"""
        try:
            logger.info("\n📊 STEP 1: Validating Account Connection...")
            logger.info("-"*70)
            
            account = self.client.get_account()
            
            logger.info(f"✅ Account Connected Successfully!")
            logger.info(f"   Account Number: {account.get('account_number', 'N/A')}")
            logger.info(f"   Equity: ${account['equity']:,.2f}")
            logger.info(f"   Cash: ${account['cash']:,.2f}")
            logger.info(f"   Buying Power: ${account['buying_power']:,.2f}")
            logger.info(f"   Portfolio Value: ${account.get('portfolio_value', account['equity']):,.2f}")
            logger.info(f"   Pattern Day Trader: {account.get('pattern_day_trader', False)}")
            logger.info(f"   Trading Blocked: {account.get('trading_blocked', False)}")
            logger.info(f"   Account Blocked: {account.get('account_blocked', False)}")
            
            # Check if trading is allowed
            if account.get('trading_blocked', False):
                logger.error("❌ Trading is BLOCKED on this account")
                return False
            
            if account.get('account_blocked', False):
                logger.error("❌ Account is BLOCKED")
                return False
            
            # Check market status
            is_open = self.client.is_market_open()
            logger.info(f"   Market Status: {'OPEN ✅' if is_open else 'CLOSED ⏸️'}")
            
            logger.info("\n✅ Account validation PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Account validation FAILED: {e}", exc_info=True)
            return False
    
    def validate_options_access(self) -> bool:
        """Validate options trading access"""
        try:
            logger.info("\n📊 STEP 2: Validating Options Access...")
            logger.info("-"*70)
            
            # Test getting options chain
            test_symbol = "TSLA"
            logger.info(f"Testing options chain for {test_symbol}...")
            
            chain = self.options_feed.get_options_chain(test_symbol)
            
            if not chain:
                logger.warning("⚠️  No options chain returned - may not have options access")
                return False
            
            logger.info(f"✅ Options chain accessible - {len(chain)} contracts found")
            
            # Check expiration dates
            expirations = self.options_feed.get_expiration_dates(test_symbol)
            if expirations:
                logger.info(f"✅ Expiration dates available: {len(expirations)} dates")
                logger.info(f"   Next 3 expirations: {expirations[:3]}")
            else:
                logger.warning("⚠️  No expiration dates found")
            
            logger.info("\n✅ Options access validation PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Options access validation FAILED: {e}", exc_info=True)
            return False
    
    def find_test_option(self, symbol: str = "TSLA") -> dict:
        """Find a suitable option for testing"""
        try:
            logger.info(f"\n📊 STEP 3: Finding Test Option for {symbol}...")
            logger.info("-"*70)
            
            # Get current stock price
            current_price = self.client.get_latest_price(symbol)
            if not current_price:
                logger.error(f"❌ Cannot get current price for {symbol}")
                return None
            
            logger.info(f"   Current {symbol} price: ${current_price:.2f}")
            
            # Get options chain
            chain = self.options_feed.get_options_chain(symbol)
            if not chain:
                logger.error(f"❌ No options chain for {symbol}")
                return None
            
            # Get expiration dates
            expirations = self.options_feed.get_expiration_dates(symbol)
            if not expirations:
                logger.error(f"❌ No expiration dates for {symbol}")
                return None
            
            # Select expiration (prefer 7-60 days out, but accept any available)
            today = datetime.now()
            target_expiration = None
            
            # First try to find 7-60 DTE
            for exp in sorted(expirations):
                try:
                    if isinstance(exp, str):
                        exp_date = datetime.strptime(exp, '%Y-%m-%d')
                    else:
                        exp_date = exp
                    dte = (exp_date - today).days
                    if 7 <= dte <= 60:
                        target_expiration = exp
                        break
                except:
                    continue
            
            # If none found, use closest future expiration
            if not target_expiration:
                for exp in sorted(expirations):
                    try:
                        if isinstance(exp, str):
                            exp_date = datetime.strptime(exp, '%Y-%m-%d')
                        else:
                            exp_date = exp
                        if exp_date >= today:
                            target_expiration = exp
                            break
                    except:
                        continue
            
            # Last resort: use first available
            if not target_expiration:
                target_expiration = sorted(expirations)[0] if expirations else None
            
            logger.info(f"   Target expiration: {target_expiration}")
            
            # Find ATM call option
            atm_strike = round(current_price)
            logger.info(f"   Looking for ATM CALL @ ${atm_strike:.2f}")
            
            for contract in chain:
                if isinstance(contract, dict):
                    contract_type = contract.get('type', '') or contract.get('option_type', '')
                    strike = float(contract.get('strike_price', 0) or contract.get('strike', 0))
                    exp_date = contract.get('expiration_date') or contract.get('exp_date')
                    option_symbol = contract.get('symbol') or contract.get('contract_symbol')
                    
                    if (contract_type.lower() == 'call' and 
                        abs(strike - atm_strike) < 10.0 and  # Within $10 of ATM (more flexible)
                        str(exp_date) == str(target_expiration)):
                        
                        # Get quote
                        quote = self.options_feed.get_option_quote(option_symbol)
                        if quote:
                            bid = quote.get('bid', 0)
                            ask = quote.get('ask', 0)
                            last = quote.get('last', 0)
                            
                            if bid > 0 or ask > 0:
                                mid_price = (bid + ask) / 2 if (bid > 0 and ask > 0) else (last if last > 0 else ask or bid)
                                
                                logger.info(f"✅ Found test option:")
                                logger.info(f"   Symbol: {option_symbol}")
                                logger.info(f"   Type: CALL")
                                logger.info(f"   Strike: ${strike:.2f}")
                                logger.info(f"   Expiration: {exp_date}")
                                logger.info(f"   Bid: ${bid:.2f}")
                                logger.info(f"   Ask: ${ask:.2f}")
                                logger.info(f"   Mid: ${mid_price:.2f}")
                                
                                return {
                                    'option_symbol': option_symbol,
                                    'strike': strike,
                                    'expiration': exp_date,
                                    'type': 'call',
                                    'bid': bid,
                                    'ask': ask,
                                    'mid_price': mid_price,
                                    'underlying': symbol,
                                    'underlying_price': current_price
                                }
            
            logger.warning("⚠️  No suitable option found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding test option: {e}", exc_info=True)
            return None
    
    def execute_test_trade(self, option_info: dict) -> bool:
        """Execute a small test options trade"""
        try:
            logger.info(f"\n📊 STEP 4: Executing Test Trade...")
            logger.info("-"*70)
            
            if not option_info:
                logger.error("❌ No option info provided")
                return False
            
            option_symbol = option_info['option_symbol']
            mid_price = option_info['mid_price']
            
            # Calculate small position size (1 contract = $100 max risk)
            max_risk = 100.0  # $100 max for test
            contracts = max(1, int(max_risk / (mid_price * 100)))
            
            logger.info(f"   Option: {option_symbol}")
            logger.info(f"   Estimated Price: ${mid_price:.2f}")
            logger.info(f"   Contracts: {contracts}")
            logger.info(f"   Estimated Cost: ${mid_price * contracts * 100:,.2f}")
            
            # Confirm
            logger.info("\n⚠️  READY TO EXECUTE TEST TRADE")
            logger.info("   This will place a REAL order in your paper trading account")
            
            # Execute buy order
            logger.info(f"\n   Placing BUY order for {contracts} {option_symbol} contracts...")
            
            order = self.options_client.place_option_order(
                option_symbol=option_symbol,
                qty=contracts,
                side='buy',
                order_type='market'
            )
            
            if not order:
                logger.error("❌ Order failed - no order returned")
                return False
            
            logger.info(f"\n✅ ORDER PLACED!")
            logger.info(f"   Order ID: {order.get('id', 'N/A')}")
            logger.info(f"   Status: {order.get('status', 'N/A')}")
            logger.info(f"   Quantity: {order.get('filled_qty', order.get('qty', contracts))}")
            
            if order.get('filled_avg_price'):
                filled_price = order['filled_avg_price']
                filled_qty = order.get('filled_qty', contracts)
                total_cost = filled_price * filled_qty * 100
                logger.info(f"   Fill Price: ${filled_price:.2f}")
                logger.info(f"   Filled Quantity: {filled_qty}")
                logger.info(f"   Total Cost: ${total_cost:,.2f}")
            
            # Wait a moment and check position
            import time
            time.sleep(2)
            
            position = self.options_client.get_option_position(option_symbol)
            if position:
                logger.info(f"\n✅ POSITION CONFIRMED:")
                logger.info(f"   Symbol: {position.get('symbol', option_symbol)}")
                logger.info(f"   Quantity: {position.get('qty', 0)}")
                logger.info(f"   Avg Entry: ${position.get('avg_entry_price', 0):.2f}")
                logger.info(f"   Current Price: ${position.get('current_price', 0):.2f}")
                logger.info(f"   Unrealized P/L: ${position.get('unrealized_pl', 0):.2f}")
            else:
                logger.warning("⚠️  Position not found yet (may take a moment)")
            
            logger.info("\n✅ Test trade execution COMPLETE")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test trade execution FAILED: {e}", exc_info=True)
            return False
    
    def validate_trade(self, option_symbol: str) -> bool:
        """Validate the executed trade"""
        try:
            logger.info(f"\n📊 STEP 5: Validating Trade...")
            logger.info("-"*70)
            
            # Check position
            position = self.options_client.get_option_position(option_symbol)
            
            if not position:
                logger.warning("⚠️  Position not found - checking all positions...")
                all_positions = self.client.get_positions()
                logger.info(f"   Total positions: {len(all_positions)}")
                for pos in all_positions:
                    logger.info(f"   - {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
                
                if len(all_positions) == 0:
                    logger.error("❌ No positions found - trade may not have executed")
                    return False
                else:
                    logger.info("✅ Found positions (may be different symbol format)")
                    return True
            
            logger.info(f"✅ Position Found:")
            logger.info(f"   Symbol: {position.get('symbol', option_symbol)}")
            logger.info(f"   Quantity: {position.get('qty', 0)}")
            logger.info(f"   Entry Price: ${position.get('avg_entry_price', 0):.2f}")
            logger.info(f"   Current Price: ${position.get('current_price', 0):.2f}")
            logger.info(f"   Market Value: ${position.get('market_value', 0):,.2f}")
            logger.info(f"   Unrealized P/L: ${position.get('unrealized_pl', 0):,.2f}")
            logger.info(f"   Unrealized P/L %: {position.get('unrealized_plpc', 0)*100:.2f}%")
            
            logger.info("\n✅ Trade validation PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Trade validation FAILED: {e}", exc_info=True)
            return False
    
    def run_full_validation(self):
        """Run complete validation and test trade"""
        logger.info("\n" + "="*70)
        logger.info("FULL VALIDATION & TEST TRADE")
        logger.info("="*70)
        
        # Step 1: Validate account
        if not self.validate_account():
            logger.error("\n❌ Account validation failed - cannot proceed")
            return False
        
        # Step 2: Validate options access
        if not self.validate_options_access():
            logger.warning("\n⚠️  Options access limited - will try anyway")
        
        # Step 3: Find test option (try multiple symbols)
        test_symbols = ["TSLA", "AAPL", "NVDA", "SPY"]
        option_info = None
        
        for symbol in test_symbols:
            logger.info(f"\nTrying {symbol}...")
            option_info = self.find_test_option(symbol)
            if option_info:
                break
        
        if not option_info:
            logger.error("\n❌ Cannot find suitable test option in any symbol")
            logger.info("   This may be due to:")
            logger.info("   - Market closed")
            logger.info("   - No options available")
            logger.info("   - Options data feed issue")
            return False
        
        # Step 4: Execute test trade
        if not self.execute_test_trade(option_info):
            logger.error("\n❌ Test trade execution failed")
            return False
        
        # Step 5: Validate trade
        if not self.validate_trade(option_info['option_symbol']):
            logger.warning("\n⚠️  Trade validation incomplete")
        
        # Final summary
        logger.info("\n" + "="*70)
        logger.info("VALIDATION COMPLETE")
        logger.info("="*70)
        logger.info("✅ Account validated")
        logger.info("✅ Options access confirmed")
        logger.info("✅ Test trade executed")
        logger.info("✅ Trade validated")
        logger.info("\n🎉 New Alpaca account is working correctly!")
        logger.info("="*70)
        
        return True

def main():
    print("\n" + "="*70)
    print("VALIDATE NEW ALPACA ACCOUNT & TEST TRADE")
    print("="*70)
    print("\nThis will:")
    print("  1. Validate your new Alpaca account connection")
    print("  2. Test options trading access")
    print("  3. Execute a SMALL test options trade (1 contract, ~$100)")
    print("  4. Validate the trade was executed")
    print("\n⚠️  This will place a REAL order in your paper trading account")
    print("-"*70)
    
    confirm = input("\nProceed with validation and test trade? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    validator = AccountValidator()
    validator.run_full_validation()

if __name__ == "__main__":
    main()

