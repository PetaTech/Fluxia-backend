from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CandlestickData(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp")
    utc_time: Optional[str] = Field(default=None, description="Human-readable UTC time")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: Optional[float] = Field(default=0, description="Volume")