from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

logger = logging.getLogger(__name__)

from app.config import config
from app.api.ea_endpoints import router as ea_router

logger.info("Starting Fluxia Backend...")

# Create FastAPI app
app = FastAPI(
    title="Fluxia EA Backend",
    description="Backend for Fluxia Expert Advisor",
    version="2.0.0"
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

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        return {
            "status": "healthy",
            "config": {
                "debug_mode": config.DEBUG
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

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