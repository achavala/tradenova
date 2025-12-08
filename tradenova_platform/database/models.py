"""
Database Models for TradeNova Platform
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    portfolio = relationship("Portfolio", back_populates="user", uselist=False)
    trades = relationship("Trade", back_populates="user")
    backtests = relationship("Backtest", back_populates="user")
    
class Subscription(Base):
    """Subscription model"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    plan = Column(String(50), default='premium')  # premium, basic, etc.
    monthly_fee = Column(Float, default=100.0)
    status = Column(String(50), default='active')  # active, cancelled, expired
    start_date = Column(DateTime, default=datetime.utcnow)
    next_billing_date = Column(DateTime)
    stripe_subscription_id = Column(String(255))
    
    # Relationships
    user = relationship("User", back_populates="subscription")

class Portfolio(Base):
    """Portfolio model - one per user"""
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    initial_balance = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)  # Balance + unrealized P&L
    cash = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Risk settings
    max_position_size_pct = Column(Float, default=10.0)  # 10% max per position
    daily_loss_limit_pct = Column(Float, default=5.0)  # 5% daily loss limit
    max_drawdown_limit_pct = Column(Float, default=15.0)  # 15% max drawdown
    max_positions = Column(Integer, default=10)
    
    # Relationships
    user = relationship("User", back_populates="portfolio")
    positions = relationship("Position", back_populates="portfolio")

class Position(Base):
    """Open position model"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    symbol = Column(String(20), nullable=False)
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    side = Column(String(10), nullable=False)  # long, short
    entry_time = Column(DateTime, default=datetime.utcnow)
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    agent_name = Column(String(100))
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")

class Trade(Base):
    """Completed trade model"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    symbol = Column(String(20), nullable=False)
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    side = Column(String(10), nullable=False)  # long, short
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    pnl = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    reason = Column(String(100))  # profit_target, stop_loss, manual, etc.
    agent_name = Column(String(100))
    commission = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="trades")

class Backtest(Base):
    """Backtest result model"""
    __tablename__ = 'backtests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255))
    tickers = Column(JSON)  # List of tickers
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Float, nullable=False)
    final_balance = Column(Float)
    total_return_pct = Column(Float)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    results_json = Column(Text)  # Full results as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="backtests")

class PerformanceMetrics(Base):
    """Daily performance metrics"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    equity = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    drawdown_pct = Column(Float, default=0.0)
    positions_count = Column(Integer, default=0)

