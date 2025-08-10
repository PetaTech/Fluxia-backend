from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CandlestickData(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: Optional[float] = Field(default=0, description="Volume")

class SubscribeRequest(BaseModel):
    currency_pair: str = Field(..., description="Currency pair (e.g., EURUSD)")
    
class SubscribeResponse(BaseModel):
    success: bool
    message: str
    candles_count: Optional[int] = None

class CandleRequest(BaseModel):
    currency_pair: str = Field(..., description="Currency pair (e.g., EURUSD)")
    count: int = Field(default=1, description="Number of latest candles to retrieve")

class CandleResponse(BaseModel):
    success: bool
    candles: List[CandlestickData]
    total_count: int
    message: Optional[str] = None

class HistoricalDataRequest(BaseModel):
    currency_pair: str = Field(..., description="Currency pair (e.g., EURUSD)")
    date: datetime = Field(..., description="Start date for historical data")
    count: int = Field(default=500, description="Number of candles to retrieve")

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None