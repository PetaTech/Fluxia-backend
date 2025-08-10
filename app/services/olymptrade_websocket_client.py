import websocket
import json
import threading
import time
import ssl
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random
import string

from app.models import CandlestickData
from app.config import config

logger = logging.getLogger(__name__)

class OlympTradeWebSocketClient:
    """OlympTrade WebSocket client using websocket-client library with working callbacks"""
    
    def __init__(self, access_token: str, full_cookie: str):
        self.access_token = access_token
        self.full_cookie = full_cookie
        self.ws = None
        self.subscribed_pairs: Dict[str, bool] = {}
        self.candlestick_callbacks: Dict[str, List[Callable]] = {}
        self._is_connected = False
        self._is_authenticated = False
        self._ws_thread = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Message handling
        self.messages = []
        self.connection_open = False
        self.candle_responses = []
        self.authenticated = False
        
        # WebSocket URL from working test
        self.ws_url = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402025.3.27106%4027106&cid_device=%40%40desktop&cid_os=windows%4010"
        
        # Headers exactly matching working Node.js example
        self.headers = [
            "Origin: https://olymptrade.com",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Pragma: no-cache",
            "Cache-Control: no-cache",
            "Accept-Encoding: gzip, deflate, br, zstd",
            "Accept-Language: en-GB,en-US;q=0.9,en;q=0.8",
            f"Cookie: {self.full_cookie}"
        ]
        
        # Enable debug if needed
        if config.DEBUG:
            websocket.enableTrace(True)
    
    def generate_uuid(self) -> str:
        """Generate UUID like OlympTrade format"""
        prefix = ''.join(random.choices(string.ascii_uppercase, k=4))
        suffix = ''.join(random.choices(string.ascii_lowercase, k=2))
        return f"{prefix}-{suffix}"
    
    def format_message(self, event_code: int, data: list, request_uuid: str = None) -> str:
        """Format message using OlympTrade protocol"""
        message_part = {
            "t": 2,  # Type 2 for client requests
            "e": event_code,
            "d": data
        }
        if request_uuid:
            message_part["uuid"] = request_uuid
        
        # Messages are lists containing one or more dictionaries
        return json.dumps([message_part])
    
    def connect(self) -> bool:
        """Connect to OlympTrade WebSocket"""
        try:
            logger.info("Connecting to OlympTrade WebSocket...")
            logger.info(f"URL: {self.ws_url}")
            
            # Create WebSocket app with proper callback signatures (closures)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                header=self.headers,
                on_message=self._create_on_message_callback(),
                on_error=self._create_on_error_callback(),
                on_close=self._create_on_close_callback(),
                on_open=self._create_on_open_callback()
            )
            
            # Run in background thread
            self._ws_thread = threading.Thread(
                target=lambda: self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}),
                daemon=True
            )
            self._ws_thread.start()
            
            # Wait for connection (up to 10 seconds)
            for i in range(50):  # 50 * 0.2s = 10s
                time.sleep(0.2)
                if self.connection_open:
                    logger.info("WebSocket connection established successfully")
                    return True
            
            logger.error("Failed to establish WebSocket connection within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to OlympTrade WebSocket: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from OlympTrade WebSocket"""
        try:
            if self.ws:
                self.ws.close()
                self.connection_open = False
                self._is_connected = False
                self._is_authenticated = False
                
            if self._ws_thread and self._ws_thread.is_alive():
                self._ws_thread.join(timeout=5)
                
            logger.info("Disconnected from OlympTrade WebSocket")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    def _create_on_message_callback(self):
        """Create on_message callback with proper signature"""
        def on_message(ws, message):
            try:
                logger.info(f"RECEIVED: {message}")
                self.messages.append(message)
                
                # Parse OlympTrade protocol message
                try:
                    data = json.loads(message)
                    if isinstance(data, list):
                        for msg_item in data:
                            event_code = msg_item.get('e')
                            msg_data = msg_item.get('d')
                            
                            logger.info(f"Event Code: {event_code}")
                            
                            if event_code == 55:  # Balance response
                                logger.info("Balance response received")
                                self.authenticated = True
                                self._is_authenticated = True
                                # Send initial subscriptions after authentication
                                self._send_initial_subscriptions()
                                
                            elif event_code == 1003:  # Candle response
                                logger.info("CANDLE RESPONSE!")
                                self.candle_responses.append(msg_item)
                                logger.info(f"Candle data: {msg_data}")
                                self._handle_olymptrade_candle_data(msg_data)
                                
                            elif event_code == 1:  # Live tick data
                                logger.info("Live tick data received")
                                self._handle_olymptrade_tick_data(msg_data)
                                
                            else:
                                # Check if this is candle data without explicit event code
                                if msg_data and isinstance(msg_data, list):
                                    for data_item in msg_data:
                                        if isinstance(data_item, dict) and 'candles' in data_item and 'p' in data_item:
                                            logger.info("CANDLE RESPONSE (no event code)!")
                                            self.candle_responses.append(msg_item)
                                            self._handle_olymptrade_candle_data(msg_data)
                                            break
                                
                                logger.debug(f"Other event {event_code}: {str(msg_item)[:100]}...")
                                
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON message received: {message}")
                    return
                    
            except Exception as e:
                logger.error(f"Error in on_message callback: {e}")
                
        return on_message
    
    def _create_on_error_callback(self):
        """Create on_error callback with proper signature"""
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        return on_error
    
    def _create_on_close_callback(self):
        """Create on_close callback with proper signature"""
        def on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
            self.connection_open = False
            self._is_connected = False
            self._is_authenticated = False
        return on_close
    
    def _create_on_open_callback(self):
        """Create on_open callback with proper signature"""
        def on_open(ws):
            logger.info("CONNECTION OPENED!")
            self.connection_open = True
            self._is_connected = True
            
            # Send authentication using OlympTrade protocol
            try:
                logger.info("Sending authentication...")
                
                # Authentication is typically done by requesting balance (event 55)
                # This initializes the session
                balance_request = self.format_message(55, [])  # Event 55 = get balance
                ws.send(balance_request)
                logger.info(f"Sent balance request: {balance_request}")
                
            except Exception as e:
                logger.error(f"Failed to send authentication message: {e}")
                
        return on_open
    
    def _send_initial_subscriptions(self):
        """Send initial subscription requests after authentication"""
        try:
            if not self.connection_open or not self._is_authenticated:
                return
                
            logger.info(" Sending initial OlympTrade subscriptions...")
            
            # Subscribe to EURUSD using OlympTrade protocol
            # Event 12: Subscribe to ticks
            tick_request_12 = self.format_message(12, [{"pair": "EURUSD"}], self.generate_uuid())
            self.ws.send(tick_request_12)
            logger.info(f" Sent event 12: {tick_request_12}")
            
            time.sleep(0.5)
            
            # Event 280: Subscribe to ticks (alternative)
            tick_request_280 = self.format_message(280, [{"pair": "EURUSD"}], self.generate_uuid())
            self.ws.send(tick_request_280)
            logger.info(f" Sent event 280: {tick_request_280}")
                    
        except Exception as e:
            logger.error(f"Error sending initial subscriptions: {e}")
    
    def _handle_olymptrade_candle_data(self, data: List[Dict[str, Any]]):
        """Handle OlympTrade candlestick data (event 1003)"""
        try:
            if not isinstance(data, list):
                logger.warning(f"Expected list for candle data, got: {type(data)}")
                return
                
            for candle_group in data:
                if not isinstance(candle_group, dict):
                    continue
                    
                pair = candle_group.get('p')
                candles = candle_group.get('candles', [])
                
                logger.info(f"Processing {len(candles)} candles for pair {pair}")
                
                for candle in candles:
                    self._process_olymptrade_single_candle(candle, pair)
                    
        except Exception as e:
            logger.error(f"Error handling OlympTrade candle data: {e}")
    
    def _handle_olymptrade_tick_data(self, data: Any):
        """Handle OlympTrade tick data (event 1)"""
        try:
            if config.DEBUG:
                logger.debug(f"Received OlympTrade tick data: {data}")
                
        except Exception as e:
            logger.error(f"Error handling OlympTrade tick data: {e}")
    
    def _process_olymptrade_single_candle(self, candle_data: Dict[str, Any], pair: Optional[str] = None):
        """Process a single OlympTrade candle and notify callbacks"""
        try:
            if not pair:
                logger.warning(f"No pair provided for candle: {candle_data}")
                return
            
            # Convert OlympTrade candle format to our CandlestickData model
            candlestick = self._convert_olymptrade_candle_to_model(candle_data)
            if not candlestick:
                return
            
            logger.debug(f"Processed candle for {pair}: {candlestick}")
            
            # Notify callbacks for this pair
            if pair in self.candlestick_callbacks:
                for callback in self.candlestick_callbacks[pair]:
                    try:
                        # Run callback in thread pool to avoid blocking
                        self._executor.submit(self._run_callback, callback, pair, candlestick)
                    except Exception as e:
                        logger.error(f"Error in candlestick callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing OlympTrade single candle: {e}")
    
    def _run_callback(self, callback: Callable, pair: str, candlestick: CandlestickData):
        """Run callback in thread pool"""
        try:
            if asyncio.iscoroutinefunction(callback):
                # Schedule async callback in the main event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule callback to run in the main event loop
                        future = asyncio.run_coroutine_threadsafe(callback(pair, candlestick), loop)
                        # Wait for completion with timeout
                        future.result(timeout=5.0)
                    else:
                        # If no loop is running, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(callback(pair, candlestick))
                        loop.close()
                except RuntimeError:
                    # Fallback: try to get running loop from different thread
                    logger.warning(f"Could not schedule async callback for {pair}, trying synchronous execution")
                    # Convert async callback to sync by running in new loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(callback(pair, candlestick))
                    loop.close()
            else:
                callback(pair, candlestick)
        except Exception as e:
            logger.error(f"Error running callback for {pair}: {e}")
            import traceback
            logger.error(f"Callback error traceback: {traceback.format_exc()}")
    
    def _convert_olymptrade_candle_to_model(self, candle_data: Dict[str, Any]) -> Optional[CandlestickData]:
        """Convert OlympTrade candle data to our model"""
        try:
            # OlympTrade format: {"t": timestamp, "open": price, "high": price, "low": price, "close": price}
            timestamp = candle_data.get('t')
            open_price = candle_data.get('open')
            high_price = candle_data.get('high')
            low_price = candle_data.get('low')
            close_price = candle_data.get('close')
            volume = 0  # OlympTrade doesn't provide volume for forex
            
            if not all([timestamp, open_price is not None, high_price is not None, 
                       low_price is not None, close_price is not None]):
                logger.warning(f"Incomplete OlympTrade candle data: {candle_data}")
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
            logger.warning(f"Failed to convert OlympTrade candle data: {candle_data}, error: {e}")
            return None
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connection_open and self._is_connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._is_authenticated
    
    def subscribe_to_candlesticks(self, currency_pair: str) -> bool:
        """Subscribe to candlestick data for a currency pair using OlympTrade protocol"""
        if not self.is_connected:
            logger.error("Not connected to OlympTrade")
            return False
        
        try:
            logger.info(f" Subscribing to {currency_pair} using OlympTrade protocol...")
            
            # Event 12: Subscribe to ticks
            tick_request_12 = self.format_message(12, [{"pair": currency_pair}], self.generate_uuid())
            self.ws.send(tick_request_12)
            logger.info(f" Sent event 12: {tick_request_12}")
            
            time.sleep(0.5)
            
            # Event 280: Subscribe to ticks (alternative)
            tick_request_280 = self.format_message(280, [{"pair": currency_pair}], self.generate_uuid())
            self.ws.send(tick_request_280)
            logger.info(f" Sent event 280: {tick_request_280}")
            
            self.subscribed_pairs[currency_pair] = True
            logger.info(f"Subscribed to candlesticks for {currency_pair}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to candlesticks for {currency_pair}: {e}")
            return False
    
    def unsubscribe_from_candlesticks(self, currency_pair: str) -> bool:
        """Unsubscribe from candlestick data for a currency pair using OlympTrade protocol"""
        if not self.is_connected:
            return False
        
        try:
            logger.info(f" Unsubscribing from {currency_pair} using OlympTrade protocol...")
            
            # Event 13: Unsubscribe from ticks
            untick_request_13 = self.format_message(13, [{"pair": currency_pair}], self.generate_uuid())
            self.ws.send(untick_request_13)
            logger.info(f" Sent event 13: {untick_request_13}")
            
            time.sleep(0.5)
            
            # Event 281: Unsubscribe from ticks (alternative)
            untick_request_281 = self.format_message(281, [{"pair": currency_pair}], self.generate_uuid())
            self.ws.send(untick_request_281)
            logger.info(f" Sent event 281: {untick_request_281}")
            
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
    
    def get_historical_candles(self, currency_pair: str, count: int, end_time: Optional[datetime] = None) -> List[CandlestickData]:
        """Request historical candlestick data using OlympTrade protocol"""
        if not self.is_connected:
            logger.error("Not connected to OlympTrade")
            return []
        
        try:
            # Calculate end timestamp
            if end_time:
                end_timestamp = int(end_time.timestamp())
            else:
                end_timestamp = int(time.time())
            
            logger.info(f"Requesting historical candles for {currency_pair} using OlympTrade protocol...")
            
            # Clear previous candle responses
            self.candle_responses.clear()
            
            # Event 10: Get candles
            candle_request = self.format_message(10, [{"pair": currency_pair, "size": 60, "to": end_timestamp, "solid": True}], self.generate_uuid())
            self.ws.send(candle_request)
            logger.info(f"Sent candle request for {currency_pair}")
            
            # Also try OTC version if currency pair doesn't end with _OTC
            if not currency_pair.endswith("_OTC"):
                time.sleep(0.5)
                otc_pair = f"{currency_pair}_OTC"
                otc_candle_request = self.format_message(10, [{"pair": otc_pair, "size": 60, "to": end_timestamp, "solid": True}], self.generate_uuid())
                self.ws.send(otc_candle_request)
                logger.info(f"Sent OTC candle request for {otc_pair}")
            
            # Wait for candle response (event 1003)
            logger.info("Waiting for candle response...")
            received_candles = []
            
            for i in range(30):  # Wait up to 15 seconds
                time.sleep(0.5)
                
                if len(self.candle_responses) > 0:
                    logger.info(f"Received {len(self.candle_responses)} candle responses")
                    
                    # Process all candle responses
                    for response in self.candle_responses:
                        candle_data_list = response.get('d', [])
                        for candle_group in candle_data_list:
                            if isinstance(candle_group, dict):
                                pair = candle_group.get('p', '')
                                candles = candle_group.get('candles', [])
                                
                                # Check if this is for our requested pair (or OTC version)
                                if pair.upper() in [currency_pair.upper(), f"{currency_pair.upper()}_OTC"]:
                                    logger.info(f"Processing {len(candles)} candles for {pair}")
                                    
                                    for candle in candles:
                                        candlestick = self._convert_olymptrade_candle_to_model(candle)
                                        if candlestick:
                                            received_candles.append(candlestick)
                    
                    if received_candles:
                        break
                        
                if i % 10 == 9:
                    logger.info(f"Still waiting for candles... ({(i+1)*0.5}s)")
            
            if received_candles:
                logger.info(f"Successfully received {len(received_candles)} historical candles for {currency_pair}")
                # Sort by timestamp (oldest first)
                received_candles.sort(key=lambda x: x.timestamp)
                return received_candles
            else:
                logger.warning(f"No historical candles received for {currency_pair}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get historical candles for {currency_pair}: {e}")
            return []
    
    def send_ping(self):
        """Send ping to keep connection alive"""
        if self.is_connected:
            try:
                ping_msg = {"type": "ping", "timestamp": int(time.time())}
                self.ws.send(json.dumps(ping_msg))
            except Exception as e:
                logger.error(f"Failed to send ping: {e}")
                self._is_connected = False