from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fluxia_backend.log')
    ]
)

logger = logging.getLogger(__name__)

from app.config import config
from app.dependencies import (
    initialize_services, 
    startup_services, 
    shutdown_services,
    get_service_health,
    _olymp_client
)
from app.api.ea_endpoints import router as ea_router
from app.api.history_endpoints import router as history_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown"""
    try:
        # Initialize services
        logger.info("Initializing Fluxia Backend services...")
        initialize_services()
        
        # Connect to external services
        logger.info("Connecting to external services...")
        await startup_services()
        
        logger.info("Fluxia Backend started successfully!")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Fluxia Backend: {e}")
        raise
    
    finally:
        # Shutdown services
        logger.info("Shutting down Fluxia Backend...")
        await shutdown_services()
        logger.info("Fluxia Backend shut down successfully!")

# Create FastAPI app
app = FastAPI(
    title="Fluxia EA Backend",
    description="Backend service for Fluxia Expert Advisor to work with OlympTrade OTC markets",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ea_router)
app.include_router(history_router)

@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Fluxia EA Backend",
        "version": "1.0.0",
        "description": "Backend service for Fluxia Expert Advisor OTC integration",
        "endpoints": {
            "subscribe": "/ea/subscribe",
            "candlesticks": "/ea/candlesticks", 
            "status": "/ea/status/{currency_pair}",
            "unsubscribe": "/ea/unsubscribe/{currency_pair}",
            "active_subscriptions": "/ea/active-subscriptions",
            "historical_data": "/history?currency_pair={pair}&date={date}&count={count}",
            "historical_range": "/history/range?currency_pair={pair}&start_date={start}&end_date={end}",
            "health": "/health"
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = get_service_health()
        
        # Determine overall health
        olymp_healthy = health_status["olymptrade"]["connected"]
        redis_healthy = health_status["redis"]["connected"]
        
        overall_status = "healthy" if (olymp_healthy and redis_healthy) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": "2024-01-01T00:00:00Z",  # You might want to use actual timestamp
            "services": health_status,
            "config": {
                "min_candles_required": config.MIN_CANDLES_REQUIRED,
                "candle_size_seconds": config.CANDLE_SIZE_SECONDS,
                "debug_mode": config.DEBUG
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/debug/connection")
async def debug_connection():
    """Debug endpoint to check connection state"""
    if _olymp_client is None:
        return {"error": "OlympTrade client not initialized"}
    
    try:
        debug_info = {
            "client_exists": _olymp_client is not None,
            "ws_client_exists": _olymp_client.ws_client is not None,
        }
        
        if _olymp_client.ws_client:
            debug_info.update({
                "ws_connection_open": _olymp_client.ws_client.connection_open,
                "ws_internal_is_connected": getattr(_olymp_client.ws_client, '_is_connected', None),
                "ws_has_ws_object": hasattr(_olymp_client.ws_client, 'ws') and _olymp_client.ws_client.ws is not None,
                "ws_authenticated": getattr(_olymp_client.ws_client, 'authenticated', None),
            })
            
            # Now call is_connected to see what happens
            debug_info["calling_is_connected"] = "about to call..."
            debug_info["client_is_connected"] = _olymp_client.is_connected
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Debug connection failed: {e}")
        return {"error": str(e)}

@app.get("/info")
async def get_info():
    """Get system information"""
    return {
        "system": "Fluxia EA Backend",
        "version": "1.0.0",
        "olymptrade_ws_uri": config.OLYMPTRADE_WS_URI,
        "min_candles_required": config.MIN_CANDLES_REQUIRED,
        "candle_timeframe": "M1",
        "candle_size_seconds": config.CANDLE_SIZE_SECONDS,
        "supported_operations": [
            "subscribe_to_currency_pair",
            "get_real_time_candlesticks",
            "download_historical_data",
            "manage_subscriptions"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )