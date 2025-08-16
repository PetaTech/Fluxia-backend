import logging
import json
import re
from typing import Optional, Dict, Any
import requests
from datetime import datetime, timedelta
import redis
from app.config import config

logger = logging.getLogger(__name__)

class TokenService:
    """
    Manages OlympTrade access tokens using refresh tokens.
    Stores access tokens in Redis and refreshes them as needed.
    """
    
    REDIS_ACCESS_TOKEN_KEY = "olymptrade:access_token"
    REDIS_REFRESH_TOKEN_KEY = "olymptrade:refresh_token"
    
    # Fixed cookie template - only access_token will change
    COOKIE_TEMPLATE = (
        "guest_id=1000159104017761111860108393602901752901238847257934499455921160; "
        "_gcl_au=1.1.1656694393.1752901269; "
        "_ga=GA1.1.910447763.1752901271; "
        "_scid=zlNRDK6f23W-vFbqwJTAINloHYzc2-SA; "
        "__exponea_etc__=68da32d5-be5d-4fb3-93b6-66155a84c209; "
        "checked=1; "
        "lang=en_US; "
        "oauth_handler_version=2; "
        "access_token={access_token}"
    )
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(config.REDIS_URL)
            # Test connection
            self.redis_client.ping()
            logger.info("TokenService connected to Redis successfully")
        except Exception as e:
            logger.error(f"TokenService failed to connect to Redis: {e}")
            self.redis_client = None
    
    def store_refresh_token(self, refresh_token: str) -> bool:
        """Store refresh token in Redis (long-term storage)"""
        if not self.redis_client:
            return False
        try:
            # Store refresh token with 3-year expiration (refresh tokens are long-lived)
            return self.redis_client.setex(
                self.REDIS_REFRESH_TOKEN_KEY, 
                3 * 365 * 24 * 60 * 60,  # 3 years
                refresh_token
            )
        except Exception as e:
            logger.error(f"Error storing refresh token: {e}")
            return False
    
    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token from Redis"""
        if not self.redis_client:
            return None
        try:
            result = self.redis_client.get(self.REDIS_REFRESH_TOKEN_KEY)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error(f"Error getting refresh token: {e}")
            return None
    
    def store_access_token(self, access_token: str, expires_in: int = 172800) -> bool:
        """Store access token in Redis with expiration"""
        if not self.redis_client:
            return False
        try:
            # Set access token to expire in 3 days (259200 seconds)
            three_days_seconds = 3 * 24 * 60 * 60  # 259200 seconds
            return self.redis_client.setex(
                self.REDIS_ACCESS_TOKEN_KEY, 
                three_days_seconds,
                access_token
            )
        except Exception as e:
            logger.error(f"Error storing access token: {e}")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """Get access token from Redis"""
        if not self.redis_client:
            return None
        try:
            result = self.redis_client.get(self.REDIS_ACCESS_TOKEN_KEY)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using the OlympTrade refresh endpoint.
        Returns: {"success": bool, "access_token": str, "message": str}
        """
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            return {"success": False, "message": "No refresh token available"}
        
        try:
            logger.info("Refreshing access token using OlympTrade API...")
            
            # Correct OlympTrade refresh endpoint
            url = "https://gw.olymptrade.com/api/token/renew/web/v1"
            
            headers = {
                'Content-Type': 'application/json',
                'Origin': 'https://olymptrade.com',
                'Referer': 'https://olymptrade.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
                'x-cid-app': 'web@OlympTrade@2025.3.27169@27169',
                'x-cid-device': '@@desktop',
                'x-cid-os': 'windows@10',
                'x-cid-ver': '1',
                'Cookie': f'refresh_token={refresh_token}',
                'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
            }
            
            # Empty POST body as seen in DevTools
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                # Parse response body for metadata
                response_data = response.json()
                expires_in = response_data.get('expires_in', 172800)
                
                # Extract new tokens from Set-Cookie headers
                new_access_token = None
                new_refresh_token = None
                
                # Handle both single and multiple Set-Cookie headers
                set_cookies = response.headers.get('Set-Cookie', '').split(',') if response.headers.get('Set-Cookie') else []
                
                for cookie_header in set_cookies:
                    if 'access_token=' in cookie_header:
                        match = re.search(r'access_token=([^;]+)', cookie_header)
                        if match:
                            new_access_token = match.group(1)
                    
                    if 'refresh_token=' in cookie_header:
                        match = re.search(r'refresh_token=([^;]+)', cookie_header)
                        if match:
                            new_refresh_token = match.group(1)
                
                if new_access_token:
                    # Store new tokens
                    self.store_access_token(new_access_token, expires_in)
                    
                    if new_refresh_token:
                        self.store_refresh_token(new_refresh_token)
                    
                    logger.info("Successfully refreshed and stored access token")
                    return {
                        "success": True,
                        "access_token": new_access_token,
                        "expires_in": expires_in,
                        "message": "Token refreshed successfully"
                    }
                else:
                    logger.error("No access_token found in Set-Cookie headers")
                    return {"success": False, "message": "No access token in response"}
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return {
                    "success": False, 
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {"success": False, "message": str(e)}
    
    def get_full_cookie_string(self) -> Optional[str]:
        """Generate full cookie string with current access token"""
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        return self.COOKIE_TEMPLATE.format(access_token=access_token)
    
    def is_access_token_available(self) -> bool:
        """Check if we have a valid access token in Redis"""
        return self.get_access_token() is not None
    
    def initialize_from_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Initialize the token service with a refresh token.
        This will store the refresh token and get the first access token.
        """
        # Store the refresh token
        if not self.store_refresh_token(refresh_token):
            return {"success": False, "message": "Failed to store refresh token"}
        
        # Get initial access token
        return self.refresh_access_token()

# Singleton instance
token_service = None

def get_token_service() -> TokenService:
    """Get token service instance"""
    global token_service
    if token_service is None:
        token_service = TokenService()
    return token_service