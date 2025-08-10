import asyncio
import websockets
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import time

from app.models import CandlestickData
from app.config import config
from app.utils.auth_helper import create_websocket_headers, validate_jwt_token

logger = logging.getLogger(__name__)

class OlympTradeWebSocketClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.websocket = None
        self.subscribed_pairs: Dict[str, bool] = {}
        self.candlestick_callbacks: Dict[str, List[Callable]] = {}
        self._is_connected = False
        self._is_running = False
        self._message_task = None
        
        # Validate token
        token_info = validate_jwt_token(access_token)
        if token_info.get('expired'):
            logger.warning("Access token appears to be expired")
        
        # Create WebSocket headers
        self.headers = create_websocket_headers(access_token)
        
    async def connect(self) -> bool:
        """Connect to OlympTrade WebSocket with proper headers and authentication"""
        try:
            logger.info("Connecting to OlympTrade WebSocket...")
            logger.info(f"Connecting to: {config.OLYMPTRADE_WS_URI}")
            
            # Try different header parameter names based on websockets version
            try:
                # Try with extra_headers first (newer versions)
                self.websocket = await websockets.connect(
                    config.OLYMPTRADE_WS_URI,
                    extra_headers=self.headers,
                    ping_interval=20,
                    ping_timeout=10
                )
            except TypeError:
                try:
                    # Try with additional_headers (some versions)
                    header_list = [(k, v) for k, v in self.headers.items()]
                    self.websocket = await websockets.connect(
                        config.OLYMPTRADE_WS_URI,
                        additional_headers=header_list,
                        ping_interval=20,
                        ping_timeout=10
                    )
                except TypeError:
                    # Fallback: connect without custom headers
                    logger.warning("Connecting without custom headers due to websockets version compatibility")
                    self.websocket = await websockets.connect(
                        config.OLYMPTRADE_WS_URI,
                        ping_interval=20,
                        ping_timeout=10
                    )
            
            self._is_connected = True
            self._is_running = True
            
            # Start message handling task
            self._message_task = asyncio.create_task(self._handle_messages())
            
            # Send authentication message
            await self._authenticate()
            
            logger.info("Successfully connected to OlympTrade WebSocket")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to OlympTrade WebSocket: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from OlympTrade WebSocket"""
        try:
            self._is_running = False
            
            if self._message_task:
                self._message_task.cancel()
                try:
                    await self._message_task
                except asyncio.CancelledError:
                    pass
            
            if self.websocket:
                await self.websocket.close()
                
            self._is_connected = False
            logger.info("Disconnected from OlympTrade WebSocket")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected and self.websocket is not None
    
    async def _authenticate(self):
        """Send authentication message with access token"""
        try:
            auth_message = {
                "type": "auth",
                "token": self.access_token
            }
            
            await self.websocket.send(json.dumps(auth_message))
            logger.info("Sent authentication message")
            
        except Exception as e:
            logger.error(f"Failed to send authentication: {e}")
            raise
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            while self._is_running and self.websocket:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=30.0
                    )
                    
                    await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if self.websocket and not self.websocket.closed:
                        await self.websocket.ping()
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    self._is_connected = False
                    break
                    
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in message handling loop: {e}")
        finally:
            self._is_connected = False
    
    async def _process_message(self, message: str):
        """Process incoming message"""
        try:
            # Log raw message in debug mode
            if config.DEBUG:
                logger.debug(f"Received: {message}")
            
            # Try to parse as JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse message as JSON: {message[:100]}...")
                return
            
            # Handle different message types
            message_type = data.get('type')
            
            if message_type == 'auth_response':
                await self._handle_auth_response(data)
            elif message_type == 'candle_data' or 'candles' in data:
                await self._handle_candle_data(data)
            elif message_type == 'tick_data' or 'ticks' in data:
                await self._handle_tick_data(data)
            else:
                # Log unknown message types for debugging
                logger.debug(f"Unknown message type: {message_type}, data: {data}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_auth_response(self, data: Dict[str, Any]):
        """Handle authentication response"""
        try:
            success = data.get('success', False)
            if success:
                logger.info("Authentication successful")
                
                # Send initial subscriptions after successful auth
                await self._send_initial_subscriptions()
            else:
                logger.error(f"Authentication failed: {data}")
                self._is_connected = False
                
        except Exception as e:
            logger.error(f"Error handling auth response: {e}")
    
    async def _send_initial_subscriptions(self):
        """Send initial subscription requests"""
        try:
            # Subscribe to general market data first
            general_sub = {
                "type": "subscribe",
                "channels": ["market_data", "candles"]
            }
            await self.websocket.send(json.dumps(general_sub))
            
            logger.info("Sent initial subscriptions")
            
        except Exception as e:
            logger.error(f"Error sending initial subscriptions: {e}")
    
    async def _handle_candle_data(self, data: Dict[str, Any]):
        """Handle candlestick data"""
        try:
            # Extract candles from different possible formats
            candles = None
            pair = None
            
            if 'candles' in data:
                candles = data['candles']
                pair = data.get('symbol', data.get('pair'))
            elif 'data' in data and isinstance(data['data'], list):
                candles = data['data']
                pair = data.get('symbol', data.get('pair'))
            
            if candles and isinstance(candles, list):
                for candle in candles:
                    await self._process_single_candle(candle, pair)
                    
        except Exception as e:
            logger.error(f"Error handling candle data: {e}")
    
    async def _handle_tick_data(self, data: Dict[str, Any]):
        """Handle tick data (could be converted to candles)"""
        try:
            # For now, log tick data for debugging
            if config.DEBUG:
                logger.debug(f"Received tick data: {data}")
                
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    async def _process_single_candle(self, candle_data: Dict[str, Any], pair: Optional[str] = None):
        """Process a single candle and notify callbacks"""
        try:
            # Extract pair from candle data if not provided
            if not pair:
                pair = candle_data.get('symbol', candle_data.get('pair', candle_data.get('p')))
            
            if not pair:
                return  # Skip if no pair identified
            
            # Convert to our CandlestickData model
            candlestick = self._convert_to_candlestick_model(candle_data)
            if not candlestick:
                return
            
            # Notify callbacks for this pair
            if pair in self.candlestick_callbacks:
                for callback in self.candlestick_callbacks[pair]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(pair, candlestick)
                        else:
                            callback(pair, candlestick)
                    except Exception as e:
                        logger.error(f"Error in candlestick callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing single candle: {e}")
    
    def _convert_to_candlestick_model(self, candle_data: Dict[str, Any]) -> Optional[CandlestickData]:
        """Convert OlympTrade candle data to our model"""
        try:
            # Handle different possible formats
            timestamp = candle_data.get('timestamp', candle_data.get('time', candle_data.get('t')))
            open_price = candle_data.get('open', candle_data.get('o'))
            high_price = candle_data.get('high', candle_data.get('h'))
            low_price = candle_data.get('low', candle_data.get('l'))
            close_price = candle_data.get('close', candle_data.get('c'))
            volume = candle_data.get('volume', candle_data.get('v', 0))
            
            # Convert timestamp if it's in milliseconds
            if timestamp and timestamp > 10**10:
                timestamp = timestamp // 1000
            
            if not all([timestamp, open_price is not None, high_price is not None, 
                       low_price is not None, close_price is not None]):
                logger.warning(f"Incomplete candle data: {candle_data}")
                return None
            
            return CandlestickData(
                timestamp=int(timestamp),
                open=float(open_price),
                high=float(high_price),
                low=float(low_price),
                close=float(close_price),
                volume=float(volume)
            )
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert candle data: {candle_data}, error: {e}")
            return None
    
    async def subscribe_to_candlesticks(self, currency_pair: str) -> bool:
        """Subscribe to candlestick data for a currency pair"""
        if not self.is_connected:
            logger.error("Not connected to OlympTrade")
            return False
        
        try:
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "symbol": currency_pair,
                "channel": "candles",
                "timeframe": "1m"  # M1 timeframe
            }
            
            await self.websocket.send(json.dumps(subscribe_msg))
            
            # Also try alternative format
            alt_subscribe_msg = {
                "action": "subscribe",
                "pair": currency_pair,
                "type": "candle"
            }
            
            await self.websocket.send(json.dumps(alt_subscribe_msg))
            
            self.subscribed_pairs[currency_pair] = True
            logger.info(f"Subscribed to candlesticks for {currency_pair}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to candlesticks for {currency_pair}: {e}")
            return False
    
    async def unsubscribe_from_candlesticks(self, currency_pair: str) -> bool:
        """Unsubscribe from candlestick data for a currency pair"""
        if not self.is_connected:
            return False
        
        try:
            unsubscribe_msg = {
                "type": "unsubscribe",
                "symbol": currency_pair,
                "channel": "candles"
            }
            
            await self.websocket.send(json.dumps(unsubscribe_msg))
            
            self.subscribed_pairs.pop(currency_pair, None)
            logger.info(f"Unsubscribed from candlesticks for {currency_pair}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from candlesticks for {currency_pair}: {e}")
            return False
    
    def register_candlestick_callback(self, currency_pair: str, callback: Callable):
        """Register a callback for new candlestick data"""
        if currency_pair not in self.candlestick_callbacks:
            self.candlestick_callbacks[currency_pair] = []
        self.candlestick_callbacks[currency_pair].append(callback)
    
    def unregister_candlestick_callback(self, currency_pair: str, callback: Callable):
        """Unregister a callback for candlestick data"""
        if currency_pair in self.candlestick_callbacks:
            try:
                self.candlestick_callbacks[currency_pair].remove(callback)
                if not self.candlestick_callbacks[currency_pair]:
                    del self.candlestick_callbacks[currency_pair]
            except ValueError:
                pass
    
    async def get_historical_candles(self, currency_pair: str, count: int, end_time: Optional[datetime] = None) -> List[CandlestickData]:
        """Request historical candlestick data"""
        if not self.is_connected:
            logger.error("Not connected to OlympTrade")
            return []
        
        try:
            # Calculate end timestamp
            if end_time:
                end_timestamp = int(end_time.timestamp())
            else:
                end_timestamp = int(time.time())
            
            # Request historical data
            history_request = {
                "type": "history_request",
                "symbol": currency_pair,
                "timeframe": "1m",
                "count": count,
                "end_time": end_timestamp
            }
            
            await self.websocket.send(json.dumps(history_request))
            
            # For now, return empty list as we need to implement response handling
            # In a full implementation, you'd wait for the response and parse it
            logger.info(f"Requested {count} historical candles for {currency_pair}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get historical candles for {currency_pair}: {e}")
            return []
    
    async def send_ping(self):
        """Send ping to keep connection alive"""
        if self.is_connected:
            try:
                ping_msg = {"type": "ping", "timestamp": int(time.time())}
                await self.websocket.send(json.dumps(ping_msg))
            except Exception as e:
                logger.error(f"Failed to send ping: {e}")
                self._is_connected = False