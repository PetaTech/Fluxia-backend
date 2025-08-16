from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import logging
import io
import csv

from app.models import (
    CandlestickData
)
from app.services.simple_olymptrade_client import SimpleOlympTradeClient, get_simple_client
from app.services.redis_cache import redis_cache
from app.services.token_service import get_token_service
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ea", tags=["Expert Advisor"])

@router.get("/candlesticks")
async def get_candlesticks(
    currency_pair: str = Query(..., description="Currency pair (e.g., EURUSD_OTC)"),
    time: Optional[str] = Query(None, description="Specific time in YYYY-MM-DD HH:MM:SS format (UTC)"),
    download: bool = Query(False, description="Download as MetaTrader CSV file"),
    simple_client: SimpleOlympTradeClient = Depends(get_simple_client)
):
    """
    GET endpoint for historical candlesticks with optional CSV download.
    - For file downloads: Returns all latest candles
    - For EA requests with time: Returns only the searched result
    - For regular requests: Returns default amount of candles
    """
    try:
        # Check if this is an EA request (has time parameter)
        is_ea_request = time is not None
        
        # Determine count based on request type
        if download:
            request_type = "file_download"
        elif is_ea_request:
            request_type = "ea_request"
        else:
            request_type = "regular_request"
            
        logger.info(f"Fetching candles: {currency_pair}, type={request_type}, time={time}, download={download}, EA_request={is_ea_request}")
        
        # Parse specific time if provided
        end_time = None
        if time:
            try:
                end_time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid time format. Use YYYY-MM-DD HH:MM:SS")
        
        # For EA requests (with time parameter), check Redis cache first
        candles: Optional[List[CandlestickData]] = None
        if is_ea_request:
            candles = redis_cache.get_cached_candle(currency_pair, end_time)
            
        if candles is None:
            # Cache miss or not EA request - fetch from OlympTrade
            logger.info(f"Fetching from OlympTrade (cache miss or non-EA request)")
            
            # Connect, fetch, disconnect
            if not simple_client.connect():
                raise HTTPException(status_code=500, detail="Failed to connect to OlympTrade")
            
            try:
                candles = simple_client.get_historical_candles(
                    currency_pair, 
                    end_time
                )

                # If this is an EA request with a specific time, keep only the matching candle
                if is_ea_request and end_time and candles:
                    target_ts = int(end_time.replace(second=0, microsecond=0).timestamp())
                    selected = next((c for c in candles if int(c.timestamp) == target_ts), None)
                    candles = [selected] if selected else []
                    if selected:
                        # Cache the selected candle as CandlestickData (cache layer will serialize)
                        redis_cache.cache_candles(currency_pair, end_time, candles)
                    
            finally:
                simple_client.disconnect()
        else:
            logger.info(f"Using cached data for EA request")
        
        candles = candles or []

        # Add UTC time for readability (keep everything as CandlestickData in memory)
        for candle in candles:
            if candle.utc_time is None:
                utc_datetime = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc)
                candle.utc_time = utc_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Return CSV file if download=true
        if download:
            return generate_metatrader_csv(candles, currency_pair)
        
        # Return JSON response
        total_count = len(candles)
        
        return {
            "success": True,
            "candles": [
                {
                    "timestamp": candle.timestamp,
                    "utc_time": candle.utc_time,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                } for candle in candles
            ],
            "total_count": total_count
        }
        
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get candles: {str(e)}"
        )

def generate_metatrader_csv(candles: List[CandlestickData], currency_pair: str) -> StreamingResponse:
    """Generate MetaTrader compatible CSV file"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # MetaTrader CSV header: Date, Open, High, Low, Close, Tick Volume, Volume, Spread
    writer.writerow(["Date", "Open", "High", "Low", "Close", "Tick Volume", "Volume", "Spread"])
    
    # Sort candles by timestamp (oldest first) for MetaTrader
    sorted_candles = sorted(candles, key=lambda x: x.timestamp)
    
    for candle in sorted_candles:
        # Convert timestamp to MetaTrader date format (YYYY.MM.DD HH:MM)
        dt = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc)
        date_str = dt.strftime("%Y.%m.%d %H:%M")
        
        # MetaTrader CSV format
        writer.writerow([
            date_str,                    # Date
            f"{candle.open:.5f}",        # Open
            f"{candle.high:.5f}",        # High
            f"{candle.low:.5f}",         # Low
            f"{candle.close:.5f}",       # Close
            int(candle.volume),          # Tick Volume (use volume as tick volume)
            int(candle.volume),          # Volume (real volume - same as tick volume)
            "0"                          # Spread (0 for historical data)
        ])
    
    # Create filename with currency pair and timestamp
    filename = f"{currency_pair}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Token management endpoints
@router.post("/token/refresh")
async def refresh_access_token():
    """
    Manually refresh the access token using stored refresh token.
    This endpoint can be called by a cron job to refresh tokens daily.
    """
    try:
        token_service = get_token_service()
        result = token_service.refresh_access_token()
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "expires_in": result.get("expires_in"),
                "token_available": token_service.is_access_token_available()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Token refresh failed: {result['message']}"
            )
            
    except Exception as e:
        logger.error(f"Error in token refresh endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh error: {str(e)}"
        )

@router.post("/token/initialize")
async def initialize_token_service(refresh_token: str):
    """
    Initialize the token service with a refresh token.
    This should be called once to set up the refresh token.
    """
    try:
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        
        token_service = get_token_service()
        result = token_service.initialize_from_refresh_token(refresh_token)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Token service initialized successfully",
                "expires_in": result.get("expires_in"),
                "token_available": token_service.is_access_token_available()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Token initialization failed: {result['message']}"
            )
            
    except Exception as e:
        logger.error(f"Error in token initialization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Token initialization error: {str(e)}"
        )

@router.get("/token/status")
async def get_token_status():
    """
    Get current token status - whether we have a valid access token.
    """
    try:
        token_service = get_token_service()
        return {
            "access_token_available": token_service.is_access_token_available(),
            "refresh_token_available": token_service.get_refresh_token() is not None
        }
        
    except Exception as e:
        logger.error(f"Error checking token status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Token status error: {str(e)}"
        )