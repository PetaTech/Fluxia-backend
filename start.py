"""
Fluxia EA Backend Startup Script
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from app.config import config

def main():
    """Main entry point"""
    print("🚀 Starting Fluxia EA Backend...")
    print(f"📡 Host: {config.API_HOST}")
    print(f"🔌 Port: {config.API_PORT}")
    print(f"🐛 Debug: {config.DEBUG}")
    print(f"📊 Redis: {config.REDIS_URL}")
    print(f"🌐 OlympTrade WS: {config.OLYMPTRADE_WS_URI}")
    print("=" * 50)

    # Check required environment variables    
    if not config.OLYMPTRADE_REFRESH_TOKEN:
        print("❌ ERROR: OLYMPTRADE_REFRESH_TOKEN is required")
        print("Please set your OlympTrade refresh token in .env file")
        return 1
    
    try:
        # Start the server
        uvicorn.run(
            "app.main:app",
            host=config.API_HOST,
            port=config.API_PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Fluxia EA Backend...")
        return 0
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)