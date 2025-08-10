from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from datetime import datetime, timezone
import logging
import io
import csv

from app.models import HistoricalDataRequest, CandlestickData
from app.services.subscription_manager import SubscriptionManager
from app.dependencies import get_subscription_manager
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["Historical Data"])

@router.get("/")
async def download_historical_data(
    currency_pair: str = Query(..., description="Currency pair (e.g., EURUSD)"),
    date: Optional[str] = Query(None, description="Start date in ISO format (e.g., 2024-01-01T00:00:00Z)"),
    count: int = Query(default=500, description="Number of candles to retrieve", ge=1, le=2000),
    download: bool = Query(default=False, description="If true, return CSV file for download"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Download historical candlestick data for a currency pair.
    This endpoint provides historical data that can be used to populate 
    the EA with initial candles when it starts.
    
    Query Parameters:
    - currency_pair: The currency pair to get data for (e.g., EURUSD)
    - date: Start date in ISO format. If not provided, uses current time
    - count: Number of candles to retrieve (default: 500, max: 2000)
    
    Example URL: /history?currency_pair=EURUSD&date=2024-01-01T00:00:00Z&count=500
    """
    try:
        # Parse the date parameter
        start_date = None
        if date:
            try:
                # Parse ISO format date string
                start_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date format. Use ISO format (e.g., 2024-01-01T00:00:00Z): {str(e)}"
                )
        
        # Validate currency pair format
        currency_pair = currency_pair.upper().strip()
        if not currency_pair:
            raise HTTPException(
                status_code=400,
                detail="Currency pair is required"
            )
        
        logger.info(f"Fetching {count} historical candles for {currency_pair} from {start_date}")
        
        # Get historical data from OlympTrade
        historical_candles = await subscription_manager.get_historical_data(
            currency_pair=currency_pair,
            count=count,
            start_date=start_date
        )
        
        if not historical_candles:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for {currency_pair}"
            )
        
        # Sort candles by timestamp (oldest first for historical data)
        historical_candles.sort(key=lambda x: x.timestamp)
        
        # Prepare response data
        response_data = {
            "currency_pair": currency_pair,
            "start_date": start_date.isoformat() if start_date else None,
            "requested_count": count,
            "actual_count": len(historical_candles),
            "candle_size_seconds": config.CANDLE_SIZE_SECONDS,
            "candles": [
                {
                    "timestamp": candle.timestamp,
                    "datetime": datetime.fromtimestamp(candle.timestamp, tz=timezone.utc).isoformat(),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                }
                for candle in historical_candles
            ],
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "timeframe": "M1",
                "source": "OlympTrade"
            }
        }
        
        logger.info(f"Successfully retrieved {len(historical_candles)} historical candles for {currency_pair}")
        
        # Return CSV if download=true
        if download:
            return await _generate_csv_response(currency_pair, historical_candles, f"historical_data_{currency_pair}_{count}candles.csv")
        
        # Return JSON response
        return JSONResponse(
            content=response_data,
            headers={
                "Content-Type": "application/json",
                "Content-Disposition": f"attachment; filename=historical_data_{currency_pair}_{count}candles.json"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in historical data endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch historical data for {currency_pair}: {str(e)}"
        )

@router.get("/range")
async def get_historical_data_range(
    currency_pair: str = Query(..., description="Currency pair (e.g., EURUSD)"),
    start_date: str = Query(..., description="Start date in ISO format"),
    end_date: str = Query(..., description="End date in ISO format"),
    download: bool = Query(default=False, description="If true, return CSV file for download"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get historical data within a specific date range.
    This endpoint retrieves data from Redis cache if available,
    or falls back to OlympTrade API.
    
    Query Parameters:
    - currency_pair: The currency pair to get data for
    - start_date: Start date in ISO format
    - end_date: End date in ISO format
    """
    try:
        # Parse date parameters
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
                
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format. Use ISO format: {str(e)}"
            )
        
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        currency_pair = currency_pair.upper().strip()
        
        # Convert to timestamps
        start_timestamp = int(start_dt.timestamp())
        end_timestamp = int(end_dt.timestamp())
        
        # Try to get data from Redis first
        candles = await subscription_manager.redis_service.get_candlesticks_range(
            currency_pair, start_timestamp, end_timestamp
        )
        
        # If no data in Redis, try to fetch from OlympTrade
        if not candles:
            logger.info(f"No cached data found for {currency_pair}, fetching from OlympTrade")
            # Calculate approximate count needed
            time_diff_seconds = end_timestamp - start_timestamp
            estimated_candles = time_diff_seconds // config.CANDLE_SIZE_SECONDS
            
            candles = await subscription_manager.get_historical_data(
                currency_pair=currency_pair,
                count=min(estimated_candles, 2000),  # Limit to 2000 candles
                start_date=end_dt  # Get data ending at end_date
            )
            
            # Filter to the requested range
            candles = [
                candle for candle in candles
                if start_timestamp <= candle.timestamp <= end_timestamp
            ]
        
        # Sort by timestamp
        candles.sort(key=lambda x: x.timestamp)
        
        # Return CSV if download=true
        if download:
            filename = f"historical_range_{currency_pair}_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.csv"
            return await _generate_csv_response(currency_pair, candles, filename)
        
        # Return JSON response
        response_data = {
            "currency_pair": currency_pair,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "candle_count": len(candles),
            "candles": [
                {
                    "timestamp": candle.timestamp,
                    "datetime": datetime.fromtimestamp(candle.timestamp, tz=timezone.utc).isoformat(),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                }
                for candle in candles
            ]
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in historical range endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch historical range data: {str(e)}"
        )

async def _generate_csv_response(currency_pair: str, candles: list, filename: str) -> StreamingResponse:
    """Generate CSV response in MetaTrader format"""
    try:
        # Create CSV content in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header in MetaTrader format
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Tick Volume", "Volume", "Spread"])
        
        # Write candle data
        for candle in candles:
            # Convert timestamp to MetaTrader date format (YYYY.MM.DD HH:MM)
            dt = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc)
            date_str = dt.strftime("%Y.%m.%d %H:%M")
            
            # MetaTrader CSV format: Date, Open, High, Low, Close, Tick Volume, Volume, Spread
            # Always use exactly 5 decimal places for forex pairs (no rounding or stripping)
            # This ensures MetaTrader recognizes the correct precision
            writer.writerow([
                date_str,
                f"{candle.open:.5f}",
                f"{candle.high:.5f}", 
                f"{candle.low:.5f}",
                f"{candle.close:.5f}",
                "1",  # Default tick volume
                f"{int(candle.volume)}" if candle.volume > 0 else "0",  # Volume as integer
                "0"  # Default spread
            ])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        # Create streaming response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
        logger.info(f"Generated CSV with {len(candles)} candles for {currency_pair}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating CSV response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate CSV: {str(e)}"
        )