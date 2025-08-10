from fastapi import HTTPException
from typing import Optional
import logging

from app.services.olymptrade_client import FluxiaOlympTradeClient
from app.services.redis_service import RedisService
from app.services.subscription_manager import SubscriptionManager
from app.config import config

logger = logging.getLogger(__name__)

# Global instances - will be initialized in main.py
_olymp_client: Optional[FluxiaOlympTradeClient] = None
_redis_service: Optional[RedisService] = None
_subscription_manager: Optional[SubscriptionManager] = None

def initialize_services():
    """Initialize all services - called from main.py startup"""
    global _olymp_client, _redis_service, _subscription_manager
    
    try:
        # Validate configuration
        config.validate()
        
        # Initialize OlympTrade client
        _olymp_client = FluxiaOlympTradeClient(config.OLYMPTRADE_ACCESS_TOKEN, config.OLYMPTRADE_FULL_COOKIE)
        
        # Initialize Redis service
        _redis_service = RedisService()
        
        # Initialize subscription manager
        _subscription_manager = SubscriptionManager(_olymp_client, _redis_service)
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

async def startup_services():
    """Connect all services - called from FastAPI startup event"""
    global _olymp_client, _redis_service
    
    try:
        if _redis_service:
            redis_connected = await _redis_service.connect()
            if not redis_connected:
                raise Exception("Failed to connect to Redis")
        
        if _olymp_client:
            olymp_connected = _olymp_client.connect()
            if not olymp_connected:
                raise Exception("Failed to connect to OlympTrade")
        
        logger.info("All services connected successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect services: {e}")
        raise

async def shutdown_services():
    """Disconnect all services - called from FastAPI shutdown event"""
    global _olymp_client, _redis_service
    
    try:
        if _olymp_client:
            _olymp_client.disconnect()
            
        if _redis_service:
            await _redis_service.disconnect()
            
        logger.info("All services disconnected successfully")
        
    except Exception as e:
        logger.error(f"Error during service shutdown: {e}")

# Dependency functions for FastAPI
def get_olymp_client() -> FluxiaOlympTradeClient:
    """FastAPI dependency to get OlympTrade client"""
    if _olymp_client is None:
        raise HTTPException(
            status_code=500, 
            detail="OlympTrade client not initialized"
        )
    
    if not _olymp_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="OlympTrade client not connected"
        )
    
    return _olymp_client

def get_redis_service() -> RedisService:
    """FastAPI dependency to get Redis service"""
    if _redis_service is None:
        raise HTTPException(
            status_code=500,
            detail="Redis service not initialized"
        )
    
    if not _redis_service.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Redis service not connected"
        )
    
    return _redis_service

def get_subscription_manager() -> SubscriptionManager:
    """FastAPI dependency to get subscription manager"""
    if _subscription_manager is None:
        raise HTTPException(
            status_code=500,
            detail="Subscription manager not initialized"
        )
    
    return _subscription_manager

# Health check functions  
def check_olymp_connection() -> dict:
    """Check OlympTrade connection status"""
    debug_info = {}
    
    if _olymp_client is None:
        debug_info["client_none"] = True
        return {
            "status": "not_initialized", 
            "connected": False,
            "debug": debug_info
        }
    
    debug_info["client_exists"] = True
    debug_info["ws_client_exists"] = _olymp_client.ws_client is not None
    
    if _olymp_client.ws_client:
        debug_info["ws_connection_open"] = _olymp_client.ws_client.connection_open
        debug_info["ws_internal_connected"] = getattr(_olymp_client.ws_client, '_is_connected', None)
        debug_info["ws_has_ws_object"] = hasattr(_olymp_client.ws_client, 'ws') and _olymp_client.ws_client.ws is not None
    else:
        debug_info["ws_client_none"] = True
    
    is_connected = _olymp_client.is_connected
    debug_info["final_is_connected"] = is_connected
    
    return {
        "status": "initialized",
        "connected": is_connected,
        "subscriptions": len(_olymp_client.subscribed_pairs) if is_connected else 0,
        "debug": debug_info,
        "test_debug": "DEBUG_INFO_SHOULD_APPEAR_HERE"
    }

def check_redis_connection() -> dict:
    """Check Redis connection status"""
    if _redis_service is None:
        return {"status": "not_initialized", "connected": False}
    
    return {
        "status": "initialized", 
        "connected": _redis_service.is_connected
    }

def get_service_health() -> dict:
    """Get overall service health status"""
    with open("E:\\Upwork\\David\\Fluxia\\backend\\debug_service_health.txt", "a") as f:
        f.write("get_service_health() called\n")
        f.write("About to call check_olymp_connection()\n")
    
    olymp_result = check_olymp_connection()
    
    with open("E:\\Upwork\\David\\Fluxia\\backend\\debug_service_health.txt", "a") as f:
        f.write(f"check_olymp_connection() returned: {olymp_result}\n")
    
    return {
        "olymptrade": olymp_result,
        "redis": check_redis_connection(),
        "subscription_manager": {
            "initialized": _subscription_manager is not None,
            "active_subscriptions": len(_subscription_manager.get_active_subscriptions()) if _subscription_manager else 0
        }
    }