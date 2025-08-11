import logging
from typing import List, Optional
from datetime import datetime, timezone
import time
import json
import jwt
import requests
import websocket
import ssl
from typing import Any, Dict, List, Optional
from app.models import CandlestickData

logger = logging.getLogger(__name__)

class SimpleOlympTradeClient:
    """
    Completely simplified OlympTrade client for historical data only.
    No WebSocket subscriptions, no Redis, no callbacks, no real-time processing.
    Just connect, fetch historical data, disconnect.
    """
    
    def __init__(self, full_cookie: str, refresh_token: Optional[str] = None):
        # Extract access token from cookie string
        import re
        match = re.search(r'access_token=([^;]+)', full_cookie)
        if match:
            self.access_token = match.group(1)
        else:
            raise ValueError("No access_token found in cookie string")
        
        self.full_cookie = full_cookie
        self.refresh_token = refresh_token
        
        # WebSocket connection variables
        self.ws = None
        self._is_connected = False
        self.candle_responses = []
        self.ws_url = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402025.3.27106%4027106&cid_device=%40%40desktop&cid_os=windows%4010"
        
    def is_token_expired(self) -> bool:
        """Check if the current access token is expired"""
        try:
            decoded = jwt.decode(self.access_token, options={'verify_signature': False})
            exp = decoded.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()
                return now > exp_time
        except Exception as e:
            logger.error(f"Error checking token expiration: {e}")
            return True
        return True
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            logger.info("Refreshing access token...")
            
            # OlympTrade token refresh endpoint
            url = "https://oauth.olymptrade.com/oauth2/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                
                if new_access_token:
                    logger.info("Successfully refreshed access token")
                    self.access_token = new_access_token
                    
                    # Update the cookie string with new access token
                    import re
                    self.full_cookie = re.sub(
                        r'access_token=[^;]+',
                        f'access_token={new_access_token}',
                        self.full_cookie
                    )
                    
                    return True
                else:
                    logger.error("No access_token in refresh response")
                    return False
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
        
    def connect(self) -> bool:
        """Connect to OlympTrade WebSocket for historical data only"""
        try:
            # Check if token is expired and refresh if needed
            if self.is_token_expired():
                logger.info("Access token is expired, attempting to refresh...")
                if not self.refresh_access_token():
                    logger.error("Failed to refresh token")
                    return False
            
            # WebSocket connection
            logger.info("Connecting to OlympTrade WebSocket...")
            logger.info(f"URL: {self.ws_url}")
            
            # Create WebSocket with proper headers
            headers = [
                "Origin: https://olymptrade.com",
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Pragma: no-cache",
                "Cache-Control: no-cache",
                "Accept-Encoding: gzip, deflate, br, zstd",
                "Accept-Language: en-GB,en-US;q=0.9,en;q=0.8",
                f"Cookie: {self.full_cookie}"
            ]
            
            # Setup WebSocket callbacks
            self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
            self.ws.connect(self.ws_url, header=headers)
            self._is_connected = True
            
            # Wait for authentication
            time.sleep(2)
            logger.info("Client connected - ready for historical data only")
            return True
                
        except Exception as e:
            logger.error(f"Error connecting client: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from OlympTrade"""
        if self.ws and self._is_connected:
            self.ws.close()
            self._is_connected = False
            logger.info("Client disconnected")
    
    def generate_uuid(self) -> str:
        """Generates a unique request identifier."""
        # OlympTrade seems to use a specific format, let's mimic based on logs
        # Example: M99KQLV7C1IV4OSU8U - This looks like base36 or similar, not standard UUID
        # Using standard UUID for now, might need adjustment if format is strict
        # Update: Let's try a simpler random string based on logs like 'k7YAyt'
        import random
        import string
        # return str(uuid.uuid4())
        prefix = random.choice(string.ascii_uppercase) + \
                random.choice(string.ascii_uppercase) + \
                random.choice(string.ascii_uppercase) + \
                random.choice(string.ascii_uppercase)
        suffix = random.choice(string.ascii_lowercase) + \
                random.choice(string.ascii_lowercase)
        return f"{prefix}-{suffix}" # Example: ABCD-xy - Adjust length/chars as needed

    def format_message(self, event_code: int, data: Any, request_uuid: Optional[str] = None) -> str:
        """Formats a message payload for sending."""
        message_part = {
            "t": 2, # Type 2 for client requests
            "e": event_code,
            "d": data
        }
        if request_uuid:
            message_part["uuid"] = request_uuid
        
        # Messages seem to be lists containing one or more dictionaries
        message_list = [message_part]
        
        # Handle cases where multiple messages are sent together (seen in logs)
        # This needs more clarity - for now, assume one message per call
        
        try:
            return json.dumps(message_list)
        except TypeError as e:
            logger.error(f"Failed to serialize message data: {data} for event {event_code}. Error: {e}")
            raise
            
    def get_historical_candles(self, currency_pair: str, end_time: Optional[datetime] = None) -> List[CandlestickData]:
        if not self.ws or not self._is_connected:
            logger.error("Not connected")
            return []
        
        try:
            if end_time is None:
                to_ts = int(time.time())
            elif isinstance(end_time, datetime):
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=datetime.timezone.utc)
                to_ts = int(end_time.timestamp())
            else:
                to_ts = int(end_time)
            
            logger.info(f"Fetching historical candles for {currency_pair} ending at {datetime.fromtimestamp(to_ts)}")

            event_code_req = 10
            event_code_resp = 1003
            size = 60  # 1 minute candles
            
            data = [{"pair": currency_pair, "size": size, "to": to_ts, "solid": True}]
            request_uuid = self.generate_uuid()
            message = self.format_message(event_code_req, data, request_uuid)
            
            # Send request
            self.ws.send(message)
            logger.info(f"Sent candle request (uuid={request_uuid}) for {currency_pair}")

            # Wait for response
            timeout = 10
            start = time.time()

            while time.time() - start < timeout:
                try:
                    response = self.ws.recv()
                    if response:
                        logger.debug(f"Received raw response: {response[:2000]}")

                        # Response is a JSON array of dicts
                        messages = json.loads(response)
                        if not isinstance(messages, list):
                            logger.debug(f"Response is not list")
                            continue

                        for msg in messages:
                            # Check for matching uuid and event
                            if msg.get("uuid") == request_uuid and msg.get("e") == event_code_req:
                                candle_data = msg.get("d", [])
                                candles = []
                                for group in candle_data:
                                    if isinstance(group, dict) and group.get('p') == currency_pair:
                                        raw_candles = group.get('candles', [])
                                        for c in raw_candles:
                                            candles.append(CandlestickData(
                                                timestamp=c['t'],
                                                open=c['open'],
                                                high=c['high'],
                                                low=c['low'],
                                                close=c['close'],
                                                volume=c.get('volume', 0.0)
                                            ))
                                logger.info(f"Successfully parsed {len(candles)} candles for {currency_pair}")
                                return candles

                except Exception as e:
                    logger.error(f"Error receiving/parsing response: {e}")
                    break
            
            logger.warning(f"Timeout waiting for candle response for {currency_pair}")
            return []

        except Exception as e:
            logger.error(f"Error fetching candles for {currency_pair}: {e}")
            return []
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.ws is not None and self._is_connected


# Dependency function for FastAPI
def get_simple_client() -> SimpleOlympTradeClient:
    """Get client instance for dependency injection"""
    from app.config import config
    return SimpleOlympTradeClient(
        config.OLYMP_FULL_COOKIE,
        config.OLYMPTRADE_REFRESH_TOKEN
    )