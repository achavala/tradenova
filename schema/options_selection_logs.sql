-- Options Selection Logs Schema
-- Stores reasoning trails and selection metadata for debugging, ML training, and optimization

CREATE TABLE IF NOT EXISTS options_selection_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Selection context
    ticker VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL,  -- 'buy' or 'sell'
    current_price DECIMAL(10, 2) NOT NULL,
    
    -- Selected option
    option_symbol VARCHAR(50) NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    expiry DATE NOT NULL,
    dte INTEGER NOT NULL,
    option_type VARCHAR(4) NOT NULL,  -- 'call' or 'put'
    
    -- Pricing
    price DECIMAL(10, 4) NOT NULL,
    bid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    spread_pct DECIMAL(5, 2),
    
    -- Liquidity
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    
    -- Selection metrics
    strike_distance_pct DECIMAL(5, 2) NOT NULL,  -- % from ATM
    max_price DECIMAL(10, 2) NOT NULL,  -- Dynamic max price used
    price_source VARCHAR(20),  -- 'quote', 'close_price', 'close_price_fallback'
    
    -- Market context
    market_open BOOLEAN NOT NULL,
    selection_time_ms INTEGER NOT NULL,  -- Selection time in milliseconds
    
    -- Reasoning trail (JSON)
    reasoning JSONB,
    
    -- Filter statistics (for debugging)
    filter_stats JSONB,
    
    -- Indexes for common queries
    INDEX idx_ticker_timestamp (ticker, timestamp),
    INDEX idx_timestamp (timestamp),
    INDEX idx_option_symbol (option_symbol),
    INDEX idx_expiry (expiry)
);

-- Example reasoning JSON structure:
-- {
--   "atm_distance_pct": 0.3,
--   "volume": 0,
--   "open_interest": 38291,
--   "spread_abs": 0.05,
--   "spread_pct": 2.0,
--   "spread_acceptable": true,
--   "price_within_max": true,
--   "time_aware_pricing": "close_price_fallback"
-- }

-- Example filter_stats JSON structure:
-- {
--   "total": 100,
--   "dte_out_of_range": 0,
--   "wrong_type": 26,
--   "strike_too_far": 0,
--   "no_price": 0,
--   "price_out_of_range": 10,
--   "no_liquidity": 5,
--   "no_bid_ask": 0,
--   "spread_too_wide": 0,
--   "passed": 1
-- }

