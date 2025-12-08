# TradeNova Platform Setup Guide

## Overview
Complete setup guide for the TradeNova multi-user trading platform.

## Prerequisites
- Python 3.9+
- PostgreSQL (for production) or SQLite (for development)
- Alpaca API account (paper trading)
- Stripe account (for payments)

## Installation

### 1. Install Dependencies
```bash
cd TradeNova
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python -c "
from tradenova_platform.database.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///platform.db')
Base.metadata.create_all(engine)
print('Database initialized!')
"
```

### 3. Configure Environment Variables
Create `.env` file:
```bash
# Alpaca API
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database
DATABASE_URL=sqlite:///platform.db  # or postgresql://user:pass@localhost/db

# JWT Secret (change in production!)
JWT_SECRET=your-super-secret-jwt-key-change-this

# Stripe (for payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 4. Start API Server
```bash
uvicorn tradenova_platform.api.routes:app --reload --port 8000
```

### 5. Start User Dashboard
```bash
streamlit run tradenova_platform/web/user_dashboard.py --server.port 8503
```

## Usage

### Create First User
```python
from tradenova_platform.user_manager import UserManager

manager = UserManager()
user = manager.create_user(
    email="user@example.com",
    username="trader1",
    password="secure_password",
    full_name="John Doe",
    initial_balance=10000.0
)
print(f"User created: {user['username']}")
```

### API Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get token

#### Portfolio
- `GET /api/portfolio` - Get portfolio
- `GET /api/portfolio/positions` - Get open positions
- `GET /api/portfolio/trades` - Get trade history
- `GET /api/portfolio/performance` - Get performance metrics

#### Trading
- `POST /api/trading/start` - Start automated trading
- `POST /api/trading/stop` - Stop automated trading
- `GET /api/trading/status` - Get trading status

#### Backtesting
- `POST /api/backtest/run` - Run backtest
- `GET /api/backtest/history` - Get backtest history

## Security Considerations

1. **Change JWT Secret**: Update `JWT_SECRET` in production
2. **Use HTTPS**: Always use HTTPS in production
3. **Database Security**: Use PostgreSQL with proper credentials
4. **API Rate Limiting**: Implement rate limiting
5. **User Fund Protection**: Each user's funds are isolated

## Scaling for 1000+ Users

### Database
- Use PostgreSQL for production
- Implement connection pooling
- Add database indexes
- Regular backups

### API Server
- Use multiple workers: `uvicorn --workers 4`
- Implement Redis for caching
- Add load balancer (nginx)
- Monitor with Prometheus/Grafana

### Trading Engine
- Queue system for trade execution
- Separate worker processes
- Rate limiting per user
- Circuit breakers

## Payment Integration (Stripe)

1. Get Stripe API keys
2. Configure webhook endpoint
3. Handle subscription events
4. Update user subscription status

## Monitoring

- API logs: Check uvicorn logs
- Database: Monitor query performance
- Trading: Track execution times
- Errors: Set up error tracking (Sentry)

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review API documentation at `/docs`
- Check database for data integrity

