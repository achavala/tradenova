"""
FastAPI Routes for TradeNova Platform
RESTful API for user management, trading, and backtesting
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from tradenova_platform.user_manager import UserManager
from tradenova_platform.portfolio_manager import PortfolioManager
from tradenova_platform.trading_engine import TradingEngine
from tradenova_platform.backtest_engine import BacktestEngine

app = FastAPI(title="TradeNova Platform API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize managers
user_manager = UserManager()
portfolio_manager = PortfolioManager()
trading_engine = TradingEngine()
backtest_engine = BacktestEngine()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    initial_balance: float = 0.0

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BacktestRequest(BaseModel):
    tickers: List[str]
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    initial_balance: float = 100000.0

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = user_manager.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return user_id

# Routes
@app.get("/")
async def root():
    return {"message": "TradeNova Platform API", "version": "1.0.0"}

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        user = user_manager.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            initial_balance=user_data.initial_balance
        )
        return {"message": "User created successfully", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login and get JWT token"""
    user = user_manager.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    return user

@app.get("/api/user/profile")
async def get_profile(user_id: int = Depends(get_current_user)):
    """Get user profile"""
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/portfolio")
async def get_portfolio(user_id: int = Depends(get_current_user)):
    """Get user portfolio"""
    portfolio = user_manager.get_user_portfolio(user_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@app.get("/api/portfolio/positions")
async def get_positions(user_id: int = Depends(get_current_user)):
    """Get open positions"""
    positions = portfolio_manager.get_open_positions(user_id)
    return {"positions": positions}

@app.get("/api/portfolio/trades")
async def get_trades(
    user_id: int = Depends(get_current_user),
    limit: int = 100
):
    """Get trade history"""
    trades = portfolio_manager.get_trade_history(user_id, limit=limit)
    return {"trades": trades}

@app.get("/api/portfolio/performance")
async def get_performance(user_id: int = Depends(get_current_user)):
    """Get performance metrics"""
    metrics = portfolio_manager.get_performance_metrics(user_id)
    return metrics

@app.post("/api/trading/start")
async def start_trading(user_id: int = Depends(get_current_user)):
    """Start automated trading for user"""
    try:
        result = trading_engine.start_trading(user_id)
        return {"message": "Trading started", "status": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/trading/stop")
async def stop_trading(user_id: int = Depends(get_current_user)):
    """Stop automated trading for user"""
    try:
        result = trading_engine.stop_trading(user_id)
        return {"message": "Trading stopped", "status": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/trading/status")
async def get_trading_status(user_id: int = Depends(get_current_user)):
    """Get trading status"""
    status = trading_engine.get_trading_status(user_id)
    return status

@app.post("/api/backtest/run")
async def run_backtest(
    request: BacktestRequest,
    user_id: int = Depends(get_current_user)
):
    """Run backtest for user"""
    try:
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
        
        result = backtest_engine.run_backtest(
            user_id=user_id,
            tickers=request.tickers,
            start_date=start_date,
            end_date=end_date,
            initial_balance=request.initial_balance
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/backtest/history")
async def get_backtest_history(user_id: int = Depends(get_current_user)):
    """Get backtest history"""
    history = backtest_engine.get_backtest_history(user_id)
    return {"backtests": history}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

