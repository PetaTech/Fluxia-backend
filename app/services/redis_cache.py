import redis
import json
import logging
from typing import Optional, List
from datetime import datetime, timezone
import hashlib

from app.models import CandlestickData
from app.config import config

logger = logging.getLogger(__name__)

class RedisCandleCache:
    """Redis cache for candlestick data with 5-minute expiration"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(config.REDIS_URL)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, currency_pair: str, time: Optional[datetime]) -> str:
        """Generate cache key for specific time-based EA requests"""
        if time:
            # For time-specific EA requests - round to nearest minute
            time_rounded = time.replace(second=0, microsecond=0)
            time_str = time_rounded.strftime("%Y%m%d_%H%M")
            return f"ea_candle:{currency_pair}:{time_str}"
        else:
            # For regular requests without time (not from EA)
            return f"regular_candle:{currency_pair}:latest"
    
    def get_cached_candle(self, currency_pair: str, time: Optional[datetime]) -> Optional[List[CandlestickData]]:
        """Get cached candlestick data"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(currency_pair, time)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache HIT for {cache_key}")
                data = json.loads(cached_data)
                candles = []
                for candle_data in data:
                    candles.append(CandlestickData(
                        timestamp=candle_data['timestamp'],
                        open=candle_data['open'],
                        high=candle_data['high'],
                        low=candle_data['low'],
                        close=candle_data['close'],
                        volume=candle_data.get('volume', 0)
                    ))
                return candles
            else:
                logger.info(f"Cache MISS for {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    def cache_candles(self, currency_pair: str, time: Optional[datetime], candles: List[CandlestickData]) -> bool:
        """Cache a single candlestick whose timestamp matches the given end time (5-minute expiration)."""
        if not self.redis_client or not candles or not time:
            return False

        try:
            cache_key = self._generate_cache_key(currency_pair, time)

            # Ensure JSON-serializable payload
            payload = []
            for c in candles:
                if isinstance(c, CandlestickData):
                    payload.append({
                        "timestamp": c.timestamp,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume or 0
                    })
                elif isinstance(c, dict):
                    payload.append({
                        "timestamp": c.get("timestamp"),
                        "open": c.get("open"),
                        "high": c.get("high"),
                        "low": c.get("low"),
                        "close": c.get("close"),
                        "volume": c.get("volume", 0)
                    })
                else:
                    logger.warning(f"Unsupported candle type for caching: {type(c)}")

            # Cache with 5-minute expiration (300 seconds)
            success = self.redis_client.setex(
                cache_key,
                300,  # 5 minutes
                json.dumps(payload)
            )

            if success:
                logger.info(f"Cached candle for {cache_key} (5min TTL)")
                return True
            else:
                logger.warning(f"Failed to cache candle for {cache_key}")
                return False

        except Exception as e:
            logger.error(f"Error caching candle: {e}")
            return False

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys("ea_candle:*") + self.redis_client.keys("regular_candle:*")
            
            return {
                "status": "connected",
                "total_keys": len(keys),
                "ea_keys": len([k for k in keys if k.decode().startswith("ea_candle:")]),
                "regular_keys": len([k for k in keys if k.decode().startswith("regular_candle:")]),
                "memory_used": info.get('used_memory_human', 'unknown')
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global cache instance
redis_cache = RedisCandleCache()