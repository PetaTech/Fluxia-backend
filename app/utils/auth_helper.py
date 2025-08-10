import re
import logging
from typing import Optional, Dict, Any
import json
import base64

logger = logging.getLogger(__name__)

def extract_access_token_from_cookie(cookie_string: str) -> Optional[str]:
    """
    Extract access_token from a full cookie string
    
    Args:
        cookie_string: Full cookie string like the one from the Node.js example
    
    Returns:
        Extracted access token or None if not found
    """
    try:
        # Look for access_token in the cookie string
        pattern = r'access_token=([^;]+)'
        match = re.search(pattern, cookie_string)
        
        if match:
            access_token = match.group(1)
            logger.info(f"Extracted access token: {access_token[:20]}...{access_token[-10:]}")
            return access_token
        else:
            logger.warning("No access_token found in cookie string")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting access token: {e}")
        return None

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    Validate and decode JWT token (basic validation without signature check)
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or empty dict if invalid
    """
    try:
        # Split JWT token into parts
        parts = token.split('.')
        if len(parts) != 3:
            logger.warning("Invalid JWT token format")
            return {}
        
        # Decode payload (second part)
        payload = parts[1]
        
        # Add padding if needed
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        # Base64 decode
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_payload = json.loads(decoded_bytes.decode('utf-8'))
        
        # Check expiration
        import time
        current_time = int(time.time())
        exp = decoded_payload.get('exp', 0)
        
        if exp and exp < current_time:
            logger.warning("JWT token has expired")
            decoded_payload['expired'] = True
        else:
            decoded_payload['expired'] = False
        
        logger.info(f"JWT token valid, user_id: {decoded_payload.get('user_id')}, expires: {exp}")
        return decoded_payload
        
    except Exception as e:
        logger.error(f"Error validating JWT token: {e}")
        return {}

def create_websocket_headers(access_token: str, include_cookie: bool = True) -> Dict[str, str]:
    """
    Create proper WebSocket headers for OlympTrade connection
    
    Args:
        access_token: The access token
        include_cookie: Whether to include the access token in Cookie header
    
    Returns:
        Dictionary of headers
    """
    headers = {
        'Origin': 'https://olymptrade.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    }
    
    if include_cookie and access_token:
        # Create a minimal cookie with access token
        headers['Cookie'] = f'access_token={access_token}'
    
    return headers

def parse_olymptrade_symbol(symbol: str) -> Dict[str, str]:
    """
    Parse OlympTrade symbol format
    
    Args:
        symbol: Symbol like "EURUSD", "EURUSD_OTC", etc.
    
    Returns:
        Dictionary with parsed symbol info
    """
    try:
        # Remove common suffixes
        base_symbol = symbol.upper().replace('_OTC', '').replace('.RAW', '')
        
        # Determine if it's a forex pair
        if len(base_symbol) == 6:
            base_currency = base_symbol[:3]
            quote_currency = base_symbol[3:]
            return {
                'symbol': symbol,
                'base_symbol': base_symbol,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'type': 'forex'
            }
        else:
            return {
                'symbol': symbol,
                'base_symbol': base_symbol,
                'type': 'unknown'
            }
            
    except Exception as e:
        logger.error(f"Error parsing symbol {symbol}: {e}")
        return {'symbol': symbol, 'type': 'unknown'}