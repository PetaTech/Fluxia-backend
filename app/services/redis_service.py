import redis.asyncio as redis
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
import time

from app.models import CandlestickData
from app.config import config

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        
    async def connect(self) -> bool:
        """Connect to Redis"""
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                decode_responses=True,
                max_connections=20
            )
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    @property
    def is_connected(self) -> bool:
        return self.redis_client is not None
    
    def _get_candles_key(self, currency_pair: str) -> str:
        """Get Redis key for storing candlesticks"""
        return f"{config.REDIS_CANDLES_PREFIX}{currency_pair.upper()}"
    
    def _get_subscription_key(self, currency_pair: str) -> str:
        """Get Redis key for storing subscription info"""
        return f"{config.REDIS_SUBSCRIPTION_PREFIX}{currency_pair.upper()}"
    
    async def store_candlestick(self, currency_pair: str, candlestick: CandlestickData) -> bool:
        """Store a single candlestick in Redis (sorted set by timestamp)"""
        if not self.is_connected:
            logger.error("Not connected to Redis")
            return False
            
        try:
            key = self._get_candles_key(currency_pair)
            candle_data = json.dumps({
                'timestamp': candlestick.timestamp,
                'open': candlestick.open,
                'high': candlestick.high,
                'low': candlestick.low,
                'close': candlestick.close,
                'volume': candlestick.volume
            })
            
            # Store in sorted set with timestamp as score
            await self.redis_client.zadd(key, {candle_data: candlestick.timestamp})
            
            # Keep only last 1000 candles to prevent unlimited growth
            await self.redis_client.zremrangebyrank(key, 0, -1001)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store candlestick for {currency_pair}: {e}")
            return False
    
    async def store_candlesticks_batch(self, currency_pair: str, candlesticks: List[CandlestickData]) -> bool:
        """Store multiple candlesticks in Redis efficiently"""
        if not self.is_connected or not candlesticks:
            return False
            
        try:
            key = self._get_candles_key(currency_pair)
            
            # Prepare data for batch insert
            mapping = {}
            for candle in candlesticks:
                candle_data = json.dumps({
                    'timestamp': candle.timestamp,
                    'open': candle.open,
                    'high': candle.high,
                    'low': candle.low,
                    'close': candle.close,
                    'volume': candle.volume
                })
                mapping[candle_data] = candle.timestamp
            
            # Batch insert
            await self.redis_client.zadd(key, mapping)
            
            # Keep only last 1000 candles
            await self.redis_client.zremrangebyrank(key, 0, -1001)
            
            logger.debug(f"Stored {len(candlesticks)} candlesticks for {currency_pair}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store candlesticks batch for {currency_pair}: {e}")
            return False
    
    async def get_latest_candlesticks(self, currency_pair: str, count: int = 1) -> List[CandlestickData]:
        """Get the latest N candlesticks for a currency pair"""
        if not self.is_connected:
            logger.error("Not connected to Redis")
            return []
            
        try:
            key = self._get_candles_key(currency_pair)
            
            # Get latest candlesticks (highest scores first)
            raw_candles = await self.redis_client.zrevrange(key, 0, count - 1, withscores=False)
            
            candlesticks = []
            for candle_str in raw_candles:
                try:
                    candle_data = json.loads(candle_str)
                    candlestick = CandlestickData(**candle_data)
                    candlesticks.append(candlestick)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse candlestick data: {candle_str}, error: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            candlesticks.sort(key=lambda x: x.timestamp, reverse=True)
            return candlesticks
            
        except Exception as e:
            logger.error(f"Failed to get latest candlesticks for {currency_pair}: {e}")
            return []
    
    async def get_candlesticks_count(self, currency_pair: str) -> int:
        """Get the total count of stored candlesticks for a currency pair"""
        if not self.is_connected:
            return 0
            
        try:
            key = self._get_candles_key(currency_pair)
            count = await self.redis_client.zcard(key)
            return count
            
        except Exception as e:
            logger.error(f"Failed to get candlesticks count for {currency_pair}: {e}")
            return 0
    
    async def get_candlesticks_range(self, currency_pair: str, start_time: int, end_time: int) -> List[CandlestickData]:
        """Get candlesticks within a timestamp range"""
        if not self.is_connected:
            return []
            
        try:
            key = self._get_candles_key(currency_pair)
            
            # Get candlesticks in timestamp range
            raw_candles = await self.redis_client.zrangebyscore(key, start_time, end_time)
            
            candlesticks = []
            for candle_str in raw_candles:
                try:
                    candle_data = json.loads(candle_str)
                    candlestick = CandlestickData(**candle_data)
                    candlesticks.append(candlestick)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse candlestick data: {candle_str}")
                    continue
            
            return candlesticks
            
        except Exception as e:
            logger.error(f"Failed to get candlesticks range for {currency_pair}: {e}")
            return []
    
    async def set_subscription_status(self, currency_pair: str, subscribed: bool, metadata: Optional[dict] = None) -> bool:
        """Set subscription status for a currency pair"""
        if not self.is_connected:
            return False
            
        try:
            key = self._get_subscription_key(currency_pair)
            
            data = {
                'subscribed': subscribed,
                'timestamp': int(time.time()),
                'metadata': metadata or {}
            }
            
            await self.redis_client.set(key, json.dumps(data), ex=3600)  # Expire in 1 hour
            return True
            
        except Exception as e:
            logger.error(f"Failed to set subscription status for {currency_pair}: {e}")
            return False
    
    async def get_subscription_status(self, currency_pair: str) -> Optional[dict]:
        """Get subscription status for a currency pair"""
        if not self.is_connected:
            return None
            
        try:
            key = self._get_subscription_key(currency_pair)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get subscription status for {currency_pair}: {e}")
            return None
    
    async def remove_subscription_status(self, currency_pair: str) -> bool:
        """Remove subscription status for a currency pair"""
        if not self.is_connected:
            return False
            
        try:
            key = self._get_subscription_key(currency_pair)
            await self.redis_client.delete(key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove subscription status for {currency_pair}: {e}")
            return False
    
    async def clear_candlesticks(self, currency_pair: str) -> bool:
        """Clear all candlesticks for a currency pair"""
        if not self.is_connected:
            return False
            
        try:
            key = self._get_candles_key(currency_pair)
            await self.redis_client.delete(key)
            logger.info(f"Cleared candlesticks for {currency_pair}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear candlesticks for {currency_pair}: {e}")
            return False