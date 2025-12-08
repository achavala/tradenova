"""
User Management System
Handles user authentication, subscriptions, and account management
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import jwt
import bcrypt
from pathlib import Path

from tradenova_platform.database.models import Base, User, Subscription, Portfolio

logger = logging.getLogger(__name__)

class UserManager:
    """Manages users, authentication, and subscriptions"""
    
    def __init__(self, database_url: str = "sqlite:///platform.db"):
        """
        Initialize user manager
        
        Args:
            database_url: Database connection string
        """
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        import os
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
        
    def create_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        initial_balance: float = 0.0
    ) -> Dict:
        """
        Create a new user account
        
        Args:
            email: User email
            username: Username
            password: Plain text password
            full_name: Full name
            initial_balance: Initial portfolio balance
            
        Returns:
            User dictionary
        """
        db = self.SessionLocal()
        try:
            # Check if user exists
            if db.query(User).filter(User.email == email).first():
                raise ValueError("User with this email already exists")
            if db.query(User).filter(User.username == username).first():
                raise ValueError("Username already taken")
            
            # Hash password
            password_hash = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Create user
            user = User(
                email=email,
                username=username,
                password_hash=password_hash,
                full_name=full_name,
                is_active=True
            )
            db.add(user)
            db.flush()
            
            # Create subscription
            subscription = Subscription(
                user_id=user.id,
                plan='premium',
                monthly_fee=100.0,
                status='active',
                start_date=datetime.utcnow(),
                next_billing_date=datetime.utcnow() + timedelta(days=30)
            )
            db.add(subscription)
            
            # Create portfolio
            portfolio = Portfolio(
                user_id=user.id,
                initial_balance=initial_balance,
                current_balance=initial_balance,
                equity=initial_balance,
                cash=initial_balance
            )
            db.add(portfolio)
            
            db.commit()
            
            logger.info(f"Created user: {username} ({email})")
            
            return {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            db.close()
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user and return JWT token
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User dict with token or None
        """
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return None
            
            if not user.is_active:
                return None
            
            # Verify password
            if not bcrypt.checkpw(
                password.encode('utf-8'),
                user.password_hash.encode('utf-8')
            ):
                return None
            
            # Generate JWT token
            token = jwt.encode(
                {
                    'user_id': user.id,
                    'email': user.email,
                    'exp': datetime.utcnow() + timedelta(days=30)
                },
                self.jwt_secret,
                algorithm='HS256'
            )
            
            return {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'token': token
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
        finally:
            db.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat(),
                'is_active': user.is_active
            }
        finally:
            db.close()
    
    def verify_token(self, token: str) -> Optional[int]:
        """
        Verify JWT token and return user_id
        
        Args:
            token: JWT token
            
        Returns:
            user_id or None
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_portfolio(self, user_id: int) -> Optional[Dict]:
        """Get user's portfolio"""
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.portfolio:
                return None
            
            portfolio = user.portfolio
            
            return {
                'user_id': user_id,
                'initial_balance': portfolio.initial_balance,
                'current_balance': portfolio.current_balance,
                'equity': portfolio.equity,
                'cash': portfolio.cash,
                'total_pnl': portfolio.total_pnl,
                'total_return_pct': portfolio.total_return_pct,
                'max_drawdown_pct': portfolio.max_drawdown_pct,
                'win_rate': portfolio.win_rate,
                'sharpe_ratio': portfolio.sharpe_ratio,
                'last_updated': portfolio.last_updated.isoformat(),
                'risk_settings': {
                    'max_position_size_pct': portfolio.max_position_size_pct,
                    'daily_loss_limit_pct': portfolio.daily_loss_limit_pct,
                    'max_drawdown_limit_pct': portfolio.max_drawdown_limit_pct,
                    'max_positions': portfolio.max_positions
                }
            }
        finally:
            db.close()

