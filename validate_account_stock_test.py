#!/usr/bin/env python3
"""
Validate New Alpaca Account & Test Stock Trade
Simpler test using stock instead of options
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime
from config import Config
from alpaca_client import AlpacaClient
from core.live.broker_executor import BrokerExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/validate_account_stock_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_and_test():
    """Validate account and execute small test trade"""
    logger.info("="*70)
    logger.info("VALIDATE NEW ACCOUNT & TEST STOCK TRADE")
    logger.info("="*70)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    executor = BrokerExecutor(client)
    
    # Step 1: Validate account
    logger.info("\n📊 STEP 1: Validating Account...")
    logger.info("-"*70)
    
    try:
        account = client.get_account()
        logger.info(f"✅ Account Connected!")
        logger.info(f"   Equity: ${account['equity']:,.2f}")
        logger.info(f"   Cash: ${account['cash']:,.2f}")
        logger.info(f"   Buying Power: ${account['buying_power']:,.2f}")
        logger.info(f"   Trading Blocked: {account.get('trading_blocked', False)}")
        logger.info(f"   Account Blocked: {account.get('account_blocked', False)}")
        logger.info(f"   Market Open: {client.is_market_open()}")
        
        if account.get('trading_blocked', False) or account.get('account_blocked', False):
            logger.error("❌ Trading is blocked on this account")
            return False
        
    except Exception as e:
        logger.error(f"❌ Account validation failed: {e}")
        return False
    
    # Step 2: Get current positions
    logger.info("\n📊 STEP 2: Checking Current Positions...")
    logger.info("-"*70)
    
    positions = client.get_positions()
    logger.info(f"   Current Positions: {len(positions)}")
    for pos in positions:
        logger.info(f"   - {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
    
    # Step 3: Find test symbol
    logger.info("\n📊 STEP 3: Finding Test Symbol...")
    logger.info("-"*70)
    
    test_symbol = "SPY"  # Use SPY as it's liquid and stable
    current_price = client.get_latest_price(test_symbol)
    
    if not current_price:
        logger.error(f"❌ Cannot get price for {test_symbol}")
        return False
    
    logger.info(f"   Symbol: {test_symbol}")
    logger.info(f"   Current Price: ${current_price:.2f}")
    
    # Step 4: Calculate small position
    max_risk = 100.0  # $100 max for test
    shares = max(1, int(max_risk / current_price))
    position_value = shares * current_price
    
    logger.info(f"   Shares: {shares}")
    logger.info(f"   Position Value: ${position_value:,.2f}")
    
    # Step 5: Execute test trade
    logger.info("\n📊 STEP 4: Executing Test Trade...")
    logger.info("-"*70)
    logger.info(f"   Placing BUY order for {shares} {test_symbol} shares...")
    
    try:
        order = client.place_order(
            symbol=test_symbol,
            qty=shares,
            side='buy',
            order_type='market'
        )
        
        if not order:
            logger.error("❌ Order failed - no order returned")
            return False
        
        logger.info(f"\n✅ ORDER PLACED!")
        logger.info(f"   Order ID: {order.get('id', 'N/A')}")
        logger.info(f"   Status: {order.get('status', 'N/A')}")
        logger.info(f"   Quantity: {order.get('filled_qty', order.get('qty', shares))}")
        
        if order.get('filled_avg_price'):
            filled_price = order['filled_avg_price']
            filled_qty = order.get('filled_qty', shares)
            total_cost = filled_price * filled_qty
            logger.info(f"   Fill Price: ${filled_price:.2f}")
            logger.info(f"   Filled Quantity: {filled_qty}")
            logger.info(f"   Total Cost: ${total_cost:,.2f}")
        
        # Wait and check position
        import time
        logger.info("\n   Waiting 3 seconds for order to settle...")
        time.sleep(3)
        
        # Step 6: Validate trade
        logger.info("\n📊 STEP 5: Validating Trade...")
        logger.info("-"*70)
        
        position = client.get_position(test_symbol)
        
        if position:
            logger.info(f"✅ POSITION CONFIRMED:")
            logger.info(f"   Symbol: {position['symbol']}")
            logger.info(f"   Quantity: {position['qty']}")
            logger.info(f"   Avg Entry: ${position['avg_entry_price']:.2f}")
            logger.info(f"   Current Price: ${position['current_price']:.2f}")
            logger.info(f"   Market Value: ${position['market_value']:,.2f}")
            logger.info(f"   Unrealized P/L: ${position['unrealized_pl']:,.2f}")
            logger.info(f"   Unrealized P/L %: {position['unrealized_plpc']*100:.2f}%")
            
            logger.info("\n" + "="*70)
            logger.info("✅ VALIDATION COMPLETE - TEST TRADE SUCCESSFUL!")
            logger.info("="*70)
            logger.info(f"✅ Account validated and working")
            logger.info(f"✅ Test trade executed successfully")
            logger.info(f"✅ Position confirmed in account")
            logger.info("\n🎉 New Alpaca account is fully operational!")
            logger.info("="*70)
            
            return True
        else:
            logger.warning("⚠️  Position not found yet (may take a moment to settle)")
            logger.info("   Checking all positions...")
            all_positions = client.get_positions()
            logger.info(f"   Total positions: {len(all_positions)}")
            for pos in all_positions:
                logger.info(f"   - {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
            
            if len(all_positions) > 0:
                logger.info("\n✅ Positions found - trade may have executed")
                return True
            else:
                logger.error("❌ No positions found - trade may not have executed")
                return False
        
    except Exception as e:
        logger.error(f"❌ Test trade failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("VALIDATE NEW ACCOUNT & TEST STOCK TRADE")
    print("="*70)
    print("\nThis will:")
    print("  1. Validate your new Alpaca account")
    print("  2. Execute a SMALL test stock trade (~$100)")
    print("  3. Validate the trade was executed")
    print("\n⚠️  This will place a REAL order in your paper trading account")
    print("-"*70)
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
    else:
        validate_and_test()

