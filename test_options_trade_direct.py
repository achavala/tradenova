#!/usr/bin/env python3
"""
Test Options Trade - Direct Execution
Attempts to place a small options order directly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from config import Config
from alpaca_client import AlpacaClient
from core.live.options_broker_client import OptionsBrokerClient
from services.options_data_feed import OptionsDataFeed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_options_trade():
    """Test options trade execution"""
    logger.info("="*70)
    logger.info("TEST OPTIONS TRADE - DIRECT EXECUTION")
    logger.info("="*70)
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    options_client = OptionsBrokerClient(client)
    options_feed = OptionsDataFeed(client)
    
    # Get SPY options
    logger.info("\nFinding SPY option...")
    chain = options_feed.get_options_chain('SPY')
    
    if not chain:
        logger.error("No options chain available")
        return False
    
    # Find a call option near ATM
    current_price = client.get_latest_price('SPY')
    logger.info(f"SPY current price: ${current_price:.2f}")
    
    # Find ATM call
    test_option = None
    for contract in chain:
        if isinstance(contract, dict):
            opt_type = contract.get('type', '') or contract.get('option_type', '')
            symbol = contract.get('symbol') or contract.get('contract_symbol')
            strike = float(contract.get('strike_price', 0) or contract.get('strike', 0))
            
            if opt_type.lower() == 'call' and symbol and strike:
                # Find one near ATM (within $20)
                if abs(strike - current_price) < 20:
                    test_option = {
                        'symbol': symbol,
                        'strike': strike,
                        'type': 'call'
                    }
                    logger.info(f"Found test option: {symbol} CALL @ ${strike:.2f}")
                    break
    
    if not test_option:
        logger.error("No suitable option found")
        return False
    
    # Try to place order (1 contract)
    logger.info(f"\nPlacing BUY order for 1 {test_option['symbol']} contract...")
    
    try:
        order = options_client.place_option_order(
            option_symbol=test_option['symbol'],
            qty=1,
            side='buy',
            order_type='market'
        )
        
        if order:
            logger.info(f"✅ ORDER PLACED!")
            logger.info(f"   Order ID: {order.get('id', 'N/A')}")
            logger.info(f"   Status: {order.get('status', 'N/A')}")
            logger.info(f"   Symbol: {order.get('symbol', test_option['symbol'])}")
            
            # Wait and check
            import time
            time.sleep(3)
            
            position = options_client.get_option_position(test_option['symbol'])
            if position:
                logger.info(f"\n✅ POSITION CONFIRMED:")
                logger.info(f"   Symbol: {position['symbol']}")
                logger.info(f"   Quantity: {position['qty']}")
                logger.info(f"   Entry: ${position['avg_entry_price']:.2f}")
                logger.info(f"   Current: ${position['current_price']:.2f}")
                logger.info(f"   P/L: ${position['unrealized_pl']:.2f}")
                return True
            else:
                logger.warning("Position not found yet")
                return True  # Order was placed
        else:
            logger.error("Order failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_options_trade()

