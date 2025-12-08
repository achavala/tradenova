# TradeNova Platform - Multi-User Trading System

## Overview
Professional-grade multi-user trading platform designed for a community of 1000+ subscribers.

## Features

### 1. User Management
- User registration and authentication
- JWT-based authentication
- Subscription management ($100/month)
- User profiles and preferences

### 2. Portfolio Management
- Per-user isolated portfolios
- Real-time P&L tracking
- Position management
- Cash balance tracking
- Risk settings per user

### 3. Trading Engine
- Live trading execution (per user)
- Risk controls per account
- Position limits
- Daily loss limits
- Max drawdown protection

### 4. Backtesting Engine
- User-specific backtesting
- Historical performance analysis
- Strategy comparison
- Results storage

### 5. Web Dashboard
- Real-time account monitoring
- Performance charts
- Trade history
- Risk metrics
- Subscription management

## Architecture

```
tradenova_platform/
├── database/
│   └── models.py          # SQLAlchemy models
├── api/
│   └── routes.py          # FastAPI routes
├── web/
│   └── user_dashboard.py  # Streamlit dashboard
├── user_manager.py         # User management
├── portfolio_manager.py    # Portfolio management
├── trading_engine.py       # Trading execution
└── backtest_engine.py      # Backtesting
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize database:
```bash
python -c "from tradenova_platform.database.models import Base; from sqlalchemy import create_engine; engine = create_engine('sqlite:///platform.db'); Base.metadata.create_all(engine)"
```

3. Start API server:
```bash
uvicorn platform.api.routes:app --reload --port 8000
```

4. Start web dashboard:
```bash
streamlit run platform/web/dashboard.py --server.port 8503
```

## Security

- Encrypted password storage (bcrypt)
- JWT token authentication
- Per-user API key isolation
- Rate limiting
- Audit logging

## Risk Management

Per-user risk settings:
- Max position size: 10% of account
- Daily loss limit: 5% of account
- Max drawdown: 15% of account
- Position limits: Max 10 concurrent
- Stop loss: 5% default
- Profit target: 10% default

## Compliance

- User fund segregation
- Performance reporting
- Risk disclosure
- Terms of service
- Privacy policy

