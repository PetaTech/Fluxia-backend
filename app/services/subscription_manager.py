import asyncio
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timezone
import time

from app.services.olymptrade_client import FluxiaOlympTradeClient
from app.services.redis_service import RedisService
from app.models import CandlestickData
from app.config import config

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, olymp_client: FluxiaOlympTradeClient, redis_service: RedisService):
        self.olymp_client = olymp_client
        self.redis_service = redis_service
        self.active_subscriptions: Set[str] = set()
        self.subscription_lock = asyncio.Lock()
        
    async def subscribe_to_pair(self, currency_pair: str) -> tuple[bool, str, int]:
        """
        Subscribe to a currency pair for real-time candlestick data
        Returns: (success, message, candles_count)
        """
        currency_pair = currency_pair.upper()
        
        async with self.subscription_lock:
            # Check if already subscribed
            if currency_pair in self.active_subscriptions:
                candles_count = await self.redis_service.get_candlesticks_count(currency_pair)
                return True, f"Already subscribed to {currency_pair}", candles_count
            
            try:
                # Temporarily bypass connection check - we know WebSocket works from direct tests
                logger.info(f"Attempting subscription to {currency_pair} - bypassing connection check for testing")
                
                # Register callback for this currency pair
                self.olymp_client.register_candlestick_callback(
                    currency_pair, 
                    self._handle_new_candlestick
                )
                
                # Subscribe to OlympTrade
                success = self.olymp_client.subscribe_to_candlesticks(currency_pair)
                if not success:
                    self.olymp_client.unregister_candlestick_callback(
                        currency_pair, 
                        self._handle_new_candlestick
                    )
                    return False, f"Failed to subscribe to OlympTrade for {currency_pair}", 0
                
                # Mark as subscribed
                self.active_subscriptions.add(currency_pair)
                
                # Update Redis subscription status
                await self.redis_service.set_subscription_status(
                    currency_pair, 
                    True, 
                    {'subscribed_at': int(time.time())}
                )
                
                # Populate initial historical data
                await self.populate_initial_data(currency_pair, 500)
                
                # Get current candles count
                candles_count = await self.redis_service.get_candlesticks_count(currency_pair)
                
                logger.info(f"Successfully subscribed to {currency_pair}, current candles: {candles_count}")
                return True, f"Successfully subscribed to {currency_pair}", candles_count
                
            except Exception as e:
                logger.error(f"Error subscribing to {currency_pair}: {e}")
                return False, f"Error subscribing to {currency_pair}: {str(e)}", 0
    
    async def unsubscribe_from_pair(self, currency_pair: str) -> tuple[bool, str]:
        """
        Unsubscribe from a currency pair
        Returns: (success, message)
        """
        currency_pair = currency_pair.upper()
        
        async with self.subscription_lock:
            if currency_pair not in self.active_subscriptions:
                return True, f"Not subscribed to {currency_pair}"
            
            try:
                # Unsubscribe from OlympTrade
                self.olymp_client.unsubscribe_from_candlesticks(currency_pair)
                
                # Unregister callback
                self.olymp_client.unregister_candlestick_callback(
                    currency_pair, 
                    self._handle_new_candlestick
                )
                
                # Remove from active subscriptions
                self.active_subscriptions.discard(currency_pair)
                
                # Update Redis subscription status
                await self.redis_service.remove_subscription_status(currency_pair)
                
                logger.info(f"Successfully unsubscribed from {currency_pair}")
                return True, f"Successfully unsubscribed from {currency_pair}"
                
            except Exception as e:
                logger.error(f"Error unsubscribing from {currency_pair}: {e}")
                return False, f"Error unsubscribing from {currency_pair}: {str(e)}"
    
    async def get_subscription_status(self, currency_pair: str) -> dict:
        """Get subscription status for a currency pair"""
        currency_pair = currency_pair.upper()
        
        is_active = currency_pair in self.active_subscriptions
        candles_count = await self.redis_service.get_candlesticks_count(currency_pair)
        redis_status = await self.redis_service.get_subscription_status(currency_pair)
        
        return {
            'currency_pair': currency_pair,
            'is_subscribed': is_active,
            'candles_count': candles_count,
            'has_minimum_candles': candles_count >= config.MIN_CANDLES_REQUIRED,
            'redis_status': redis_status
        }
    
    async def get_latest_candlesticks(self, currency_pair: str, count: int = 1) -> list[CandlestickData]:
        """Get the latest candlesticks for a currency pair"""
        currency_pair = currency_pair.upper()
        
        if currency_pair not in self.active_subscriptions:
            logger.warning(f"Requesting candlesticks for unsubscribed pair: {currency_pair}")
        
        return await self.redis_service.get_latest_candlesticks(currency_pair, count)
    
    async def get_historical_data(self, currency_pair: str, count: int, start_date: Optional[datetime] = None) -> list[CandlestickData]:
        """
        Get historical candlestick data from OlympTrade
        This is used for the historical data download endpoint
        """
        currency_pair = currency_pair.upper()
        
        try:
            if not self.olymp_client.is_connected:
                logger.error("OlympTrade client not connected")
                return []
            
            end_time = start_date if start_date else datetime.now(timezone.utc)
            
            # Get historical data - run in thread pool to handle sync/async boundary
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                candles = await loop.run_in_executor(
                    executor,
                    self.olymp_client.get_historical_candles,
                    currency_pair,
                    count,
                    end_time
                )
            
            logger.info(f"Retrieved {len(candles)} historical candles for {currency_pair}")
            return candles
            
        except Exception as e:
            logger.error(f"Error getting historical data for {currency_pair}: {e}")
            return []
    
    async def _handle_new_candlestick(self, currency_pair: str, candlestick: CandlestickData):
        """Handle new candlestick data received from OlympTrade"""
        try:
            # Store in Redis
            await self.redis_service.store_candlestick(currency_pair, candlestick)
            
            logger.debug(f"Stored new candlestick for {currency_pair}: {candlestick.timestamp}")
            
        except Exception as e:
            logger.error(f"Error handling new candlestick for {currency_pair}: {e}")
    
    async def populate_initial_data(self, currency_pair: str, count: int = 500) -> bool:
        """
        Populate initial historical data for a currency pair
        This helps avoid the 500 candles wait time for EA
        """
        currency_pair = currency_pair.upper()
        
        try:
            # Check current count
            current_count = await self.redis_service.get_candlesticks_count(currency_pair)
            if current_count >= count:
                logger.info(f"Already have {current_count} candles for {currency_pair}")
                return True
            
            needed_count = count - current_count
            logger.info(f"Fetching {needed_count} initial candles for {currency_pair}")
            
            # Get historical data - run in thread pool to handle sync/async boundary
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                historical_candles = await loop.run_in_executor(
                    executor,
                    self.olymp_client.get_historical_candles,
                    currency_pair,
                    needed_count,
                    None
                )
            
            if historical_candles:
                # Store in Redis
                await self.redis_service.store_candlesticks_batch(currency_pair, historical_candles)
                final_count = await self.redis_service.get_candlesticks_count(currency_pair)
                logger.info(f"Populated {len(historical_candles)} candles for {currency_pair}, total: {final_count}")
                return True
            else:
                logger.warning(f"No historical data received for {currency_pair}")
                return False
                
        except Exception as e:
            logger.error(f"Error populating initial data for {currency_pair}: {e}")
            return False
    
    async def cleanup_old_subscriptions(self):
        """Clean up old subscription data and inactive subscriptions"""
        try:
            # This could be called periodically to clean up Redis data
            # for pairs that are no longer being tracked
            for currency_pair in list(self.active_subscriptions):
                status = await self.redis_service.get_subscription_status(currency_pair)
                if not status:
                    # If Redis status is missing, the subscription might be stale
                    logger.warning(f"Removing stale subscription for {currency_pair}")
                    self.active_subscriptions.discard(currency_pair)
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_active_subscriptions(self) -> set[str]:
        """Get the set of currently active subscriptions"""
        return self.active_subscriptions.copy()
    
    async def request_fresh_candle(self, currency_pair: str) -> bool:
        """Request the latest candle using Event 10"""
        currency_pair = currency_pair.upper()
        
        try:
            if not self.olymp_client.ws_client or not self.olymp_client.ws_client.connection_open:
                logger.error("WebSocket not connected")
                return False
            
            current_time = int(time.time())
            logger.info(f"Requesting fresh candle for {currency_pair} at timestamp {current_time}")
            
            # Send Event 10 request for latest candle
            candle_request = self.olymp_client.ws_client.format_message(
                10, 
                [{"pair": currency_pair, "size": 60, "to": current_time, "solid": True}],
                self.olymp_client.ws_client.generate_uuid()
            )
            
            self.olymp_client.ws_client.ws.send(candle_request)
            logger.info(f"Sent Event 10 candle request for {currency_pair}: {candle_request}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error requesting fresh candle for {currency_pair}: {e}")
            return False