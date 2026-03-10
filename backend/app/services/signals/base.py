"""
signals/base.py
Abstract base class that every signal collector inherits from.

Phase 2 signals (reviews, adverse_media, social, stock) receive an optional
canonical_domain parameter — the root domain discovered by WebsiteSignal in
Phase 1 (e.g. "apple.com"). They should use this to anchor their queries and
avoid cross-company contamination.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from app.schemas.response import SignalResult


class BaseSignal(ABC):
    name: str = "base"

    @abstractmethod
    async def collect(
        self,
        business_name:    str,
        location:         str | None,
        canonical_domain: str | None = None,
    ) -> SignalResult:
        """Run the signal collection and return a normalised SignalResult."""
        ...

    def _error_result(self, exc: Exception) -> SignalResult:
        return SignalResult(
            name=self.name,
            status="error",
            summary=f"{self.name} signal failed: {str(exc)}",
            sources=[],
        )