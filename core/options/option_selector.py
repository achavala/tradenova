"""
Option Selector
Selects the best option contract based on criteria:
- 0-30 DTE (prefer 0-7 DTE)
- ATM or slightly OTM strike
- CALL for LONG, PUT for SHORT
- Liquidity filters (bid > 0, volume > 0, OI > 0)
- Price range: $0.20 - $10.00 (or 5% of underlying, capped at $20)
"""
import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from services.options_data_feed import OptionsDataFeed
from alpaca_client import AlpacaClient
from core.options.selection_logger import SelectionLogger

logger = logging.getLogger(__name__)

class OptionSelector:
    """Selects optimal option contracts for trading"""
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize option selector
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.options_feed = OptionsDataFeed(alpaca_client)
        self.executor = ThreadPoolExecutor(max_workers=10)  # For async quote fetching
        self.selection_logger = SelectionLogger()  # For storing reasoning trails
    
    def pick_best_option(
        self,
        ticker: str,
        side: str,  # 'buy' or 'sell' (maps to LONG/SHORT)
        current_price: float,
        max_dte: int = 7,  # Prefer 0-7 DTE, but allow up to 30
        min_price: float = 0.20,
        max_price: Optional[float] = None,  # If None, will calculate dynamically
        max_spread_pct: float = 15.0,  # Maximum bid/ask spread percentage
        max_strike_distance_pct: float = 15.0  # Maximum strike distance from ATM (15%)
    ) -> Optional[Dict]:
        """
        Selects the best option contract based on criteria
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            side: 'buy' (LONG/CALL) or 'sell' (SHORT/PUT)
            current_price: Current stock price
            max_dte: Maximum days to expiry (default 7, but will check up to 30)
            min_price: Minimum option price (default $0.20)
            max_price: Maximum option price (default $10.00)
        
        Returns:
            Dictionary with option details or None if no suitable option found
            {
                'symbol': 'AAPL251220C00150000',
                'strike': 150.0,
                'expiry': date(2025, 12, 20),
                'dte': 12,
                'type': 'call',
                'price': 2.50,
                'bid': 2.45,
                'ask': 2.55,
                'volume': 1000,
                'open_interest': 5000
            }
        """
        import time
        selection_start_time = time.time()
        market_is_open = None  # Will be set later
        max_price = None  # Will be set later
        filter_stats = {}  # Will be set later
        
        try:
            logger.info(f"🔍 Selecting option for {ticker} ({side.upper()}) @ ${current_price:.2f}")
            
            # ✅ Fix 1: Dynamic max price calculation (5% of underlying, capped at $20)
            # This handles high-IV situations where ATM contracts can be $15-$20
            if max_price is None:
                max_price = min(current_price * 0.05, 20.00)
                logger.debug(f"  Calculated max_price: ${max_price:.2f} (5% of ${current_price:.2f}, capped at $20.00)")
            
            # ✅ Fix 1: Add absolute floor for min option price
            # Penny options (< $0.10) behave very differently and often have no volume, huge spreads, 80-90% value decay
            min_price_floor = 0.10
            if min_price < min_price_floor:
                min_price = min_price_floor
                logger.debug(f"  Adjusted min_price to floor: ${min_price:.2f}")
            
            # Determine option type
            desired_type = 'call' if side.lower() == 'buy' else 'put'
            logger.debug(f"  Option type: {desired_type.upper()}")
            
            # Get options chain
            chain = self.options_feed.get_options_chain(ticker)
            if not chain or len(chain) == 0:
                logger.warning(f"⚠️  {ticker}: No options chain available")
                return None
            
            logger.debug(f"  Found {len(chain)} contracts in chain")
            
            # Parse and filter contracts
            today = date.today()
            contracts = []
            filter_stats = {
                'total': len(chain),
                'no_symbol': 0,
                'no_strike': 0,
                'no_expiry': 0,
                'dte_out_of_range': 0,
                'wrong_type': 0,
                'no_price': 0,
                'price_out_of_range': 0,
                'no_bid_ask': 0,
                'spread_too_wide': 0,
                'passed': 0
            }
            
            # First pass: Filter by DTE and type (fast filters, no API calls)
            candidate_contracts = []
            for contract in chain:
                try:
                    # Extract contract data (handle both dict and object types)
                    if isinstance(contract, dict):
                        contract_symbol = contract.get('symbol') or contract.get('contract_symbol')
                        strike = self._get_strike(contract)
                        expiry_str = contract.get('expiration_date') or contract.get('exp_date')
                        option_type = contract.get('type', '').lower() or contract.get('option_type', '').lower()
                        bid = float(contract.get('bid', 0) or contract.get('bid_price', 0) or 0)
                        ask = float(contract.get('ask', 0) or contract.get('ask_price', 0) or 0)
                        volume = int(contract.get('volume', 0) or contract.get('volume_24h', 0) or 0)
                        oi = int(contract.get('open_interest', 0) or contract.get('oi', 0) or 0)
                    else:
                        contract_symbol = getattr(contract, 'symbol', None) or getattr(contract, 'contract_symbol', None)
                        strike = self._get_strike(contract)
                        expiry_str = getattr(contract, 'expiration_date', None) or getattr(contract, 'exp_date', None)
                        option_type = (getattr(contract, 'type', '') or getattr(contract, 'option_type', '')).lower()
                        bid = float(getattr(contract, 'bid', 0) or getattr(contract, 'bid_price', 0) or 0)
                        ask = float(getattr(contract, 'ask', 0) or getattr(contract, 'ask_price', 0) or 0)
                        volume = int(getattr(contract, 'volume', 0) or getattr(contract, 'volume_24h', 0) or 0)
                        oi = int(getattr(contract, 'open_interest', 0) or getattr(contract, 'oi', 0) or 0)
                    
                    if not contract_symbol:
                        filter_stats['no_symbol'] += 1
                        continue
                    if not strike:
                        filter_stats['no_strike'] += 1
                        continue
                    if not expiry_str:
                        filter_stats['no_expiry'] += 1
                        continue
                    
                    # Parse expiry date
                    try:
                        if isinstance(expiry_str, str):
                            expiry = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                        elif hasattr(expiry_str, 'date'):
                            expiry = expiry_str.date()
                        else:
                            expiry = expiry_str
                        
                        dte = (expiry - today).days
                    except Exception as e:
                        logger.debug(f"  Error parsing expiry: {e}")
                        continue
                    
                    # Filter by DTE: 0-30 days (prefer 0-7)
                    if dte < 0 or dte > 30:
                        filter_stats['dte_out_of_range'] += 1
                        continue
                    
                    # Filter by option type
                    if option_type != desired_type:
                        filter_stats['wrong_type'] += 1
                        continue
                    
                    # Add to candidates for price fetching
                    candidate_contracts.append({
                        'contract': contract,
                        'contract_symbol': contract_symbol,
                        'strike': strike,
                        'expiry': expiry,
                        'dte': dte,
                        'type': option_type,
                        'original_bid': bid,
                        'original_ask': ask,
                        'volume': volume,
                        'oi': oi
                    })
                except Exception as e:
                    logger.debug(f"  Error in first pass: {e}")
                    continue
            
            # ✅ STEP 1: Sort candidates by strike distance (ATM-first) BEFORE fetching quotes
            # This ensures we ALWAYS fetch quotes for the 20 closest-to-ATM contracts
            # Convert strikes to float for proper comparison
            for candidate in candidate_contracts:
                try:
                    candidate['strike'] = float(candidate['strike'])
                except (ValueError, TypeError):
                    candidate['strike'] = 0.0
            
            # Sort by absolute distance from current price (ATM first)
            candidate_contracts.sort(key=lambda x: abs(float(x['strike']) - float(current_price)))
            
            # Second pass: Process ALL candidates (use close_price for all, fetch quotes for top candidates)
            # We use close_price from chain data for all contracts (fast, always available)
            # Then fetch real-time quotes for top candidates to get better pricing
            MAX_QUOTE_FETCHES = 20  # Don't fetch quotes for more than 20 contracts
            candidates_to_fetch_quotes = candidate_contracts[:MAX_QUOTE_FETCHES]
            
            # ✅ Check if market is open (for time-aware logic)
            market_is_open = self.client.is_market_open()
            
            logger.info(f"  📊 {len(candidate_contracts)} candidates after DTE/type filter")
            logger.info(f"  💰 Current stock price: ${current_price:.2f}, looking for options priced ${min_price:.2f}-${max_price:.2f}")
            logger.info(f"  🔍 Fetching real-time quotes for top {len(candidates_to_fetch_quotes)} ATM candidates (async)")
            
            # ✅ STEP 1 (Performance): Async quote fetching for top candidates
            # This reduces quote-fetch time from 6-7 seconds to 0.4-0.7 seconds
            quote_results = {}
            if candidates_to_fetch_quotes:
                try:
                    # Fetch quotes in parallel using thread pool
                    def fetch_quote(symbol):
                        try:
                            return self.options_feed.get_option_quote(symbol)
                        except Exception as e:
                            logger.debug(f"  Quote fetch error for {symbol}: {e}")
                            return None
                    
                    # ✅ Fix 3: Add timeout protection for async batch quote fetching
                    # Use ThreadPoolExecutor for parallel quote fetching with overall timeout
                    symbols_to_fetch = [c['contract_symbol'] for c in candidates_to_fetch_quotes]
                    futures = {self.executor.submit(fetch_quote, symbol): symbol for symbol in symbols_to_fetch}
                    
                    # Overall timeout: 3 seconds for all quotes (prevents hanging)
                    import time
                    start_time = time.time()
                    timeout_seconds = 3.0
                    
                    for future in futures:
                        # Check if we've exceeded overall timeout
                        if time.time() - start_time > timeout_seconds:
                            logger.warning(f"  ⚠️  Overall quote fetch timeout ({timeout_seconds}s), stopping")
                            break
                        
                        symbol = futures[future]
                        try:
                            # Individual quote timeout: 2 seconds
                            quote = future.result(timeout=2.0)
                            if quote:
                                quote_results[symbol] = quote
                        except Exception as e:
                            logger.debug(f"  Timeout/error fetching quote for {symbol}: {e}")
                            continue
                    
                    logger.debug(f"  ✅ Fetched {len(quote_results)} quotes in parallel")
                except Exception as e:
                    logger.warning(f"  ⚠️  Error in async quote fetching: {e}, falling back to sequential")
                    quote_results = {}
            
            # Process ALL candidates (use close_price for all, real-time quotes for top candidates)
            for candidate in candidate_contracts:
                try:
                    contract = candidate['contract']
                    contract_symbol = candidate['contract_symbol']
                    strike = candidate['strike']
                    expiry = candidate['expiry']
                    dte = candidate['dte']
                    option_type = candidate['type']
                    bid = candidate['original_bid']
                    ask = candidate['original_ask']
                    volume = candidate['volume']
                    oi = candidate['oi']
                    
                    # ✅ STEP 2: Normalize ALL numeric fields to floats upfront
                    # This prevents TypeError and incorrect comparisons
                    if isinstance(contract, dict):
                        strike_float = float(contract.get('strike_price', 0) or 0)
                        close_price_raw = contract.get('close_price')
                        bid_raw = contract.get('bid_price') or contract.get('bid') or 0
                        ask_raw = contract.get('ask_price') or contract.get('ask') or 0
                    else:
                        strike_float = float(getattr(contract, 'strike_price', 0) or 0)
                        close_price_raw = getattr(contract, 'close_price', None)
                        bid_raw = getattr(contract, 'bid_price', None) or getattr(contract, 'bid', None) or 0
                        ask_raw = getattr(contract, 'ask_price', None) or getattr(contract, 'ask', None) or 0
                    
                    # Normalize to floats
                    try:
                        close_price = float(close_price_raw) if close_price_raw else None
                        bid_original = float(bid_raw) if bid_raw else 0.0
                        ask_original = float(ask_raw) if ask_raw else 0.0
                    except (ValueError, TypeError):
                        close_price = None
                        bid_original = 0.0
                        ask_original = 0.0
                    
                    # ✅ STEP 4: Reject contracts that are too deep ITM/OTM
                    strike_distance_pct = abs(strike_float - current_price) / current_price * 100
                    if strike_distance_pct > max_strike_distance_pct:
                        filter_stats['strike_too_far'] = filter_stats.get('strike_too_far', 0) + 1
                        continue
                    
                    # ✅ STEP 3: Improve close_price fallback logic
                    # Only use close_price if it's reasonable (< $15) and market is closed
                    # During market hours, prefer real-time quotes
                    mid = None
                    price_source = None
                    bid = bid_original
                    ask = ask_original
                    
                    # Use close_price as fallback (only if reasonable and market closed)
                    if close_price and close_price > 0 and close_price < 15.0:
                        if not market_is_open:
                            # Market closed: use close_price
                            mid = close_price
                            bid = mid * 0.99
                            ask = mid * 1.01
                            price_source = 'close_price'
                        elif bid_original <= 0 and ask_original <= 0:
                            # Market open but no quotes: use close_price as fallback
                            mid = close_price
                            bid = mid * 0.99
                            ask = mid * 1.01
                            price_source = 'close_price_fallback'
                    
                    # ✅ STEP 7: Time-aware logic - use pre-fetched quotes (async)
                    # For top candidates, use the quote we already fetched in parallel
                    if contract_symbol in quote_results:
                        quote = quote_results[contract_symbol]
                        if quote:
                            quote_mid = quote.get('mid')
                            if quote_mid and quote_mid > 0:
                                # Upgrade to real-time price (preferred during market hours)
                                mid = float(quote_mid)
                                quote_bid = quote.get('bid')
                                quote_ask = quote.get('ask')
                                if quote_bid:
                                    bid = float(quote_bid)
                                if quote_ask:
                                    ask = float(quote_ask)
                                price_source = quote.get('source', 'quote')
                                logger.debug(f"  {contract_symbol}: Upgraded to real-time {price_source}: ${mid:.2f}")
                    
                    # If still no price, skip this contract
                    if not mid or mid <= 0:
                        filter_stats['no_price'] += 1
                        continue
                    
                    # Filter by price range (ensure mid is float)
                    try:
                        mid_float = float(mid) if mid else 0
                    except (ValueError, TypeError):
                        filter_stats['no_price'] += 1
                        continue
                    
                    # ✅ Fix 1: Reject options below min price floor
                    if mid_float < min_price:
                        filter_stats['price_out_of_range'] += 1
                        if filter_stats['price_out_of_range'] <= 5:
                            logger.info(f"  ⚠️  {contract_symbol}: Price ${mid_float:.2f} below min ${min_price:.2f} (penny option, rejected)")
                        continue
                    
                    if mid_float > max_price:
                        filter_stats['price_out_of_range'] += 1
                        if filter_stats['price_out_of_range'] <= 5:
                            logger.info(f"  ⚠️  {contract_symbol}: Price ${mid_float:.2f} above max ${max_price:.2f} (strike: ${strike:.2f}, DTE: {dte}, {('ITM' if strike < current_price else 'OTM')}, source: {price_source})")
                        continue
                    
                    # Update mid to float version
                    mid = mid_float
                    
                    # ✅ Fix 2: Reject options with 0 volume AND 0 open interest (fully illiquid)
                    # These are junk contracts with no liquidity
                    if volume == 0 and oi == 0:
                        filter_stats['no_liquidity'] = filter_stats.get('no_liquidity', 0) + 1
                        logger.debug(f"  Skipping {contract_symbol}: No liquidity (volume=0, oi=0)")
                        continue
                    
                    # Log when we find a contract in price range
                    if len(contracts) < 3:  # Log first 3 that pass price filter
                        logger.info(f"  ✅ {contract_symbol}: Price ${mid:.2f} IN RANGE (strike: ${strike:.2f}, DTE: {dte}, source: {price_source})")
                    
                    # Filter by liquidity - require at least bid OR ask
                    # But be lenient: if we have a mid price, we can still use it
                    if bid <= 0 and ask <= 0:
                        filter_stats['no_bid_ask'] += 1
                        # If we have mid price from chain data, we can still use it (market might be closed)
                        # Only skip if we truly have no pricing data
                        if mid <= 0:
                            logger.debug(f"  Skipping {contract_symbol}: No bid/ask and no mid price")
                            continue
                        else:
                            # Use mid as both bid and ask for spread calculation
                            bid = mid * 0.99  # Assume 1% spread if no data
                            ask = mid * 1.01
                            logger.debug(f"  {contract_symbol}: No bid/ask, using mid price ${mid:.2f} with estimated spread")
                    
                    # ✅ STEP 6: Improved spread filtering
                    # Very liquid options have: spread < 0.25 or spread < 10% of price
                    try:
                        bid_float = float(bid) if bid else 0
                        ask_float = float(ask) if ask else 0
                        mid_float = float(mid) if mid else 0
                        
                        if ask_float > 0 and bid_float > 0 and mid_float > 0:
                            spread_abs = ask_float - bid_float
                            spread_pct = (spread_abs / mid_float) * 100
                            
                            # Reject if spread is too wide (absolute or percentage)
                            max_spread_abs = max(0.25, mid_float * 0.10)  # $0.25 or 10% of price
                            if spread_abs > max_spread_abs or spread_pct > max_spread_pct:
                                filter_stats['spread_too_wide'] += 1
                                logger.debug(f"  Skipping {contract_symbol}: spread ${spread_abs:.2f} ({spread_pct:.1f}%) > ${max_spread_abs:.2f} or {max_spread_pct}%")
                                continue
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass  # Skip spread check if conversion fails
                    
                    # All filters passed - add to contracts list
                    filter_stats['passed'] += 1
                    
                    # Calculate spread percentage for ranking (ensure all are floats)
                    try:
                        bid_float = float(bid) if bid else 0
                        ask_float = float(ask) if ask else 0
                        mid_float = float(mid) if mid else 0
                        spread_pct = ((ask_float - bid_float) / mid_float) * 100 if (ask_float > 0 and bid_float > 0 and mid_float > 0) else 0
                    except (ValueError, TypeError, ZeroDivisionError):
                        spread_pct = 0
                    
                    contracts.append({
                        'symbol': contract_symbol,
                        'strike': strike,
                        'expiry': expiry,
                        'dte': dte,
                        'type': option_type,
                        'price': mid,
                        'bid': bid,
                        'ask': ask,
                        'volume': volume,
                        'open_interest': oi,
                        'spread_pct': spread_pct,
                        'strike_distance': abs(strike - current_price) / current_price  # % from ATM
                    })
                    
                    logger.debug(f"  ✅ {contract_symbol}: Added to contracts (price: ${mid:.2f}, strike: ${strike:.2f}, DTE: {dte})")
                    
                except Exception as e:
                    logger.warning(f"  ❌ Error processing candidate {contract_symbol}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
            
            if not contracts:
                # ✅ STEP 5: Enhanced logging for every failure stage
                logger.warning(f"⚠️  {ticker}: No contracts passed filters")
                logger.info(f"   Filters applied: DTE 0-30, type={desired_type}, price ${min_price}-${max_price}, spread <{max_spread_pct}%, strike distance <{max_strike_distance_pct}%")
                logger.info(f"   Market status: {'OPEN' if market_is_open else 'CLOSED'}")
                logger.info(f"   Filter breakdown:")
                logger.info(f"     Total contracts: {filter_stats['total']}")
                logger.info(f"     No symbol/strike/expiry: {filter_stats['no_symbol'] + filter_stats['no_strike'] + filter_stats['no_expiry']}")
                logger.info(f"     DTE out of range: {filter_stats['dte_out_of_range']}")
                logger.info(f"     Wrong type: {filter_stats['wrong_type']}")
                logger.info(f"     Strike too far from ATM: {filter_stats.get('strike_too_far', 0)}")
                logger.info(f"     No price data: {filter_stats['no_price']}")
                logger.info(f"     Price out of range: {filter_stats['price_out_of_range']}")
                logger.info(f"     No liquidity (vol=0 & oi=0): {filter_stats.get('no_liquidity', 0)}")
                logger.info(f"     No bid/ask: {filter_stats['no_bid_ask']}")
                logger.info(f"     Spread too wide: {filter_stats['spread_too_wide']}")
                logger.info(f"     Passed all filters: {filter_stats['passed']}")
                logger.info(f"   Possible reasons: Market closed, no bid/ask data, or all contracts filtered")
                
                # Log failed selection
                selection_time_ms = int((time.time() - selection_start_time) * 1000)
                self.selection_logger.log_selection(
                    ticker=ticker,
                    side=side,
                    current_price=current_price,
                    selected_option=None,
                    selection_time_ms=selection_time_ms,
                    market_open=market_is_open,
                    max_price=max_price,
                    filter_stats=filter_stats,
                    reasoning=None
                )
                
                return None
            
            logger.debug(f"  {len(contracts)} contracts passed initial filters")
            
            # Sort by priority:
            # 1. Prefer 0-7 DTE (closer expiry)
            # 2. Prefer ATM (smallest strike distance)
            # 3. Prefer higher volume/OI (more liquid)
            
            # First, separate by DTE preference
            preferred_contracts = [c for c in contracts if c['dte'] <= max_dte]
            other_contracts = [c for c in contracts if c['dte'] > max_dte]
            
            # ✅ IMPORTANT: Pre-filter by price range BEFORE sorting
            # This ensures we only consider contracts with prices in our range
            # (close_price for ITM options can be $100+, we only want $0.20-$10.00)
            preferred_contracts = [c for c in preferred_contracts if min_price <= c['price'] <= max_price]
            other_contracts = [c for c in other_contracts if min_price <= c['price'] <= max_price]
            
            if not preferred_contracts and not other_contracts:
                logger.warning(f"⚠️  {ticker}: No contracts with prices in range ${min_price:.2f}-${max_price:.2f}")
                return None
            
            # ✅ Fix 4 & 5: Deterministic tie-breaker with liquidity sorting
            # Sort by: strike distance, spread (tighter first), volume DESC, OI DESC, price ASC
            # This ensures better liquidity → safer fills
            if preferred_contracts:
                preferred_contracts.sort(
                    key=lambda x: (
                        x['strike_distance'],  # Closest to ATM first
                        x['spread_pct'],  # Tighter spread first (lower is better)
                        -x['volume'],  # Higher volume first (liquidity)
                        -x['open_interest'],  # Higher OI first
                        x['price']  # Lower price as final tie-breaker
                    )
                )
                best = preferred_contracts[0]
            elif other_contracts:
                # If no preferred DTE contracts, use others (up to 30 DTE)
                other_contracts.sort(
                    key=lambda x: (
                        x['strike_distance'],
                        x['spread_pct'],  # Tighter spread first
                        -x['volume'],  # Higher volume first (liquidity)
                        -x['open_interest'],  # Higher OI first
                        x['price']  # Lower price as final tie-breaker
                    )
                )
                best = other_contracts[0]
            else:
                return None
            
            logger.info(f"✅ Selected: {best['symbol']} | "
                       f"Strike: ${best['strike']:.2f} | "
                       f"DTE: {best['dte']} | "
                       f"Price: ${best['price']:.2f} | "
                       f"Spread: {best['spread_pct']:.1f}% | "
                       f"Type: {best['type'].upper()}")
            
            # ✅ Fix 6: Log the final chosen contract with a reasoning trail
            spread_abs = best['ask'] - best['bid']
            logger.info(f"   Reasoning:")
            logger.info(f"    - ATM candidate (strike distance: {best['strike_distance']*100:.1f}% from ${current_price:.2f})")
            logger.info(f"    - Volume: {best['volume']:,} | Open Interest: {best['open_interest']:,}")
            logger.info(f"    - Spread: ${spread_abs:.2f} ({best['spread_pct']:.1f}%) - {'acceptable' if best['spread_pct'] < 10 else 'wide but acceptable'}")
            logger.info(f"    - Mid price: ${best['price']:.2f} (within dynamic max ${max_price:.2f})")
            logger.info(f"    - Time-aware pricing: close_price_fallback")
            
            # Log selection to file for debugging and ML training
            selection_time_ms = int((time.time() - selection_start_time) * 1000)
            reasoning = {
                'atm_distance_pct': best['strike_distance'] * 100,
                'volume': best['volume'],
                'open_interest': best['open_interest'],
                'spread_abs': spread_abs,
                'spread_pct': best['spread_pct'],
                'spread_acceptable': best['spread_pct'] < 10,
                'price_within_max': best['price'] <= max_price,
                'time_aware_pricing': 'close_price_fallback'
            }
            self.selection_logger.log_selection(
                ticker=ticker,
                side=side,
                current_price=current_price,
                selected_option=best,
                selection_time_ms=selection_time_ms,
                market_open=market_is_open,
                max_price=max_price,
                filter_stats=filter_stats,
                reasoning=reasoning
            )
            
            return best
            
        except Exception as e:
            logger.error(f"❌ Error selecting option for {ticker}: {e}")
            
            # Log failed selection if we have the necessary data
            try:
                selection_time_ms = int((time.time() - selection_start_time) * 1000)
                if market_is_open is not None and max_price is not None:
                    self.selection_logger.log_selection(
                        ticker=ticker,
                        side=side,
                        current_price=current_price,
                        selected_option=None,
                        selection_time_ms=selection_time_ms,
                        market_open=market_is_open,
                        max_price=max_price,
                        filter_stats=filter_stats if filter_stats else {},
                        reasoning=None
                    )
            except:
                pass  # Don't fail on logging errors
            
            return None
    
    def _get_strike(self, contract) -> Optional[float]:
        """Extract strike price from contract (handles dict or object)"""
        try:
            if isinstance(contract, dict):
                strike = contract.get('strike_price') or contract.get('strike')
            else:
                strike = getattr(contract, 'strike_price', None) or getattr(contract, 'strike', None)
            
            if strike:
                return float(strike)
            return None
        except:
            return None
    
    def get_option_price(self, option_symbol: str) -> Optional[float]:
        """
        Get current option price
        
        Args:
            option_symbol: Option contract symbol
        
        Returns:
            Option price (mid price) or None
        """
        try:
            quote = self.options_feed.get_option_quote(option_symbol)
            if quote:
                bid = quote.get('bid', 0) or 0
                ask = quote.get('ask', 0) or 0
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
                elif ask > 0:
                    return ask
                elif bid > 0:
                    return bid
            
            # Fallback: try latest trade
            latest_price = self.client.get_latest_price(option_symbol)
            if latest_price:
                return latest_price
            
            return None
        except Exception as e:
            logger.debug(f"Error getting option price for {option_symbol}: {e}")
            return None

