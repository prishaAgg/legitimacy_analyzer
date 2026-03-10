from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class SignalResult(BaseModel):
    """Internal signal data returned by every signal collector."""
    name: str
    status: str                     # found | not_found | error | mocked
    score: Optional[float] = None   # 0–100 signal-specific score
    summary: str
    details: Optional[Any] = None   # raw data, passed through to formatter
    sources: list[str] = []
    is_mocked: bool = False


class SearchRunResponse(BaseModel):
    """Full DB record, returned by the internal /api/runs/ endpoint."""
    id: int
    business_name: str
    location: Optional[str]
    extra_context: Optional[str]
    confidence_score: Optional[float]
    verdict: Optional[str]
    verdict_summary: Optional[str]
    signals: Optional[dict[str, Any]]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SearchRunSummary(BaseModel):
    """Lightweight summary used in list responses."""
    id: int
    business_name: str
    location: Optional[str]
    confidence_score: Optional[float]
    verdict: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
