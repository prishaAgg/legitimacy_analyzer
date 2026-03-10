from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class SearchRun(Base):
    """Represents one analyst search run."""
    __tablename__ = "search_runs"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    extra_context = Column(Text, nullable=True)

    # Overall verdict
    confidence_score = Column(Float, nullable=True)      # 0–100
    verdict = Column(String(50), nullable=True)           # LIKELY_LEGIT / UNCERTAIN / RED_FLAGS
    verdict_summary = Column(Text, nullable=True)

    # Raw signal data stored as JSON blobs
    signals = Column(JSON, nullable=True)                 # dict of signal_name -> SignalResult

    # Status
    status = Column(String(20), default="pending")        # pending | running | complete | error
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
