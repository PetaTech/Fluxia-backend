import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Support both direct token and cookie string
    _raw_access_token: str = os.getenv("OLYMPTRADE_ACCESS_TOKEN", "")
    _cookie_string: str = os.getenv("OLYMPTRADE_COOKIE_STRING", "")
    
    @property
    def OLYMPTRADE_ACCESS_TOKEN(self) -> str:
        """Get access token, either directly or extracted from cookie string"""
        if self._raw_access_token:
            return self._raw_access_token
        elif self._cookie_string:
            from app.utils.auth_helper import extract_access_token_from_cookie
            return extract_access_token_from_cookie(self._cookie_string) or ""
        return ""
    
    @property
    def OLYMPTRADE_FULL_COOKIE(self) -> str:
        """Get full cookie string"""
        return self._cookie_string
    
    OLYMPTRADE_REFRESH_TOKEN: str = os.getenv("OLYMPTRADE_REFRESH_TOKEN", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # OlympTrade WebSocket URI with proper parameters
    OLYMPTRADE_WS_URI: str = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402025.3.27106%4027106&cid_device=%40%40desktop&cid_os=windows%4010"
    
    # Candlestick configuration
    CANDLE_SIZE_SECONDS: int = 60  # M1 chart
    MIN_CANDLES_REQUIRED: int = 500
    
    # Redis keys
    REDIS_CANDLES_PREFIX: str = "candles:"
    REDIS_SUBSCRIPTION_PREFIX: str = "sub:"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.OLYMPTRADE_ACCESS_TOKEN:
            raise ValueError("OLYMPTRADE_ACCESS_TOKEN is required")
        if not cls.OLYMPTRADE_REFRESH_TOKEN:
            raise ValueError("OLYMPTRADE_REFRESH_TOKEN is required")
        return True

config = Config()