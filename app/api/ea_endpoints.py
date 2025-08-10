from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import logging
import asyncio

from app.models import (
    SubscribeRequest, SubscribeResponse, 
    CandleRequest, CandleResponse, 
    ErrorResponse, CandlestickData
)
from app.services.subscription_manager import SubscriptionManager
from app.dependencies import get_subscription_manager
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ea", tags=["Expert Advisor"])

@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_to_currency_pair(
    request: SubscribeRequest,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Subscribe to a currency pair for real-time candlestick data.
    This endpoint should be called before requesting candlesticks.
    """
    try:
        success, message, candles_count = await subscription_manager.subscribe_to_pair(
            request.currency_pair
        )
        
        if success:
            # Try to populate initial data if we don't have enough candles
            if candles_count < config.MIN_CANDLES_REQUIRED:
                logger.info(f"Populating initial data for {request.currency_pair}")
                await subscription_manager.populate_initial_data(
                    request.currency_pair, 
                    config.MIN_CANDLES_REQUIRED
                )
                # Get updated count
                candles_count = await subscription_manager.redis_service.get_candlesticks_count(
                    request.currency_pair
                )
        
        return SubscribeResponse(
            success=success,
            message=message,
            candles_count=candles_count
        )
        
    except Exception as e:
        logger.error(f"Error in subscribe endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to subscribe to {request.currency_pair}: {str(e)}"
        )

@router.post("/candlesticks", response_model=CandleResponse)
async def get_candlesticks(
    request: CandleRequest,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get the latest candlestick data for a subscribed currency pair.
    EA should call this endpoint every minute to get new candles.
    """
    try:
        # Check subscription status
        status = await subscription_manager.get_subscription_status(request.currency_pair)
        
        if not status['is_subscribed']:
            return CandleResponse(
                success=False,
                candles=[],
                total_count=0,
                message=f"Not subscribed to {request.currency_pair}. Call /subscribe first."
            )
        
        # Request fresh candle first (Event 10)
        logger.info(f"Requesting fresh candle for {request.currency_pair}")
        fresh_request_success = await subscription_manager.request_fresh_candle(request.currency_pair)
        logger.info(f"Fresh candle request result: {fresh_request_success}")
        
        # Small delay to allow WebSocket response
        await asyncio.sleep(1)
        
        # Get latest candlesticks
        candles = await subscription_manager.get_latest_candlesticks(
            request.currency_pair, 
            request.count
        )
        
        total_count = await subscription_manager.redis_service.get_candlesticks_count(
            request.currency_pair
        )
        
        message = None
        if total_count < config.MIN_CANDLES_REQUIRED:
            message = (f"Warning: Only {total_count} candles available. "
                      f"EA needs {config.MIN_CANDLES_REQUIRED} candles to function properly. "
                      f"Consider downloading historical data.")
        
        return CandleResponse(
            success=True,
            candles=candles,
            total_count=total_count,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error in candlesticks endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get candlesticks for {request.currency_pair}: {str(e)}"
        )

@router.get("/status/{currency_pair}")
async def get_subscription_status(
    currency_pair: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get subscription status and candlestick count for a currency pair.
    """
    try:
        status = await subscription_manager.get_subscription_status(currency_pair)
        return status
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status for {currency_pair}: {str(e)}"
        )

@router.delete("/unsubscribe/{currency_pair}")
async def unsubscribe_from_currency_pair(
    currency_pair: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Unsubscribe from a currency pair.
    """
    try:
        success, message = await subscription_manager.unsubscribe_from_pair(currency_pair)
        
        return {
            "success": success,
            "message": message,
            "currency_pair": currency_pair
        }
        
    except Exception as e:
        logger.error(f"Error in unsubscribe endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unsubscribe from {currency_pair}: {str(e)}"
        )

@router.get("/active-subscriptions")
async def get_active_subscriptions(
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get list of all active subscriptions.
    """
    try:
        active_subs = subscription_manager.get_active_subscriptions()
        
        # Get detailed status for each subscription
        detailed_status = []
        for currency_pair in active_subs:
            status = await subscription_manager.get_subscription_status(currency_pair)
            detailed_status.append(status)
        
        return {
            "active_subscriptions": list(active_subs),
            "detailed_status": detailed_status,
            "total_count": len(active_subs)
        }
        
    except Exception as e:
        logger.error(f"Error in active-subscriptions endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active subscriptions: {str(e)}"
        )