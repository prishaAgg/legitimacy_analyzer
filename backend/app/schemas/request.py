from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze-business/ (camelCase matches frontend)."""
    businessName: str
    location: Optional[str] = None
    forceRefresh: bool = False


class SearchRequest(BaseModel):
    """Request body for the internal /api/runs/ endpoint (snake_case)."""
    business_name: str
    location: Optional[str] = None
    extra_context: Optional[str] = None
