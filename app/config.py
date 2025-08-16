import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Simplified configuration - only refresh token needed (stored in Redis via API)
    # OLYMP_FULL_COOKIE: Removed - now generated dynamically with current access token
    # OLYMPTRADE_REFRESH_TOKEN: Removed - now stored in Redis via token service
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # OlympTrade WebSocket URI with proper parameters
    OLYMPTRADE_WS_URI: str = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402025.3.27106%4027106&cid_device=%40%40desktop&cid_os=windows%4010"
    
    # Candlestick configuration
    CANDLE_SIZE_SECONDS: int = 60  # M1 chart
    
    # Redis keys
    REDIS_CANDLES_PREFIX: str = "candles:"
    REDIS_SUBSCRIPTION_PREFIX: str = "sub:"

config = Config()