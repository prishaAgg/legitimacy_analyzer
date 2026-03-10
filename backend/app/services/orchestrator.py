"""
services/orchestrator.py
Two-phase signal collection:
  Phase 1 — WebsiteSignal runs first to discover the canonical domain
             (e.g. "apple.com" for "Apple")
  Phase 2 — Remaining signals run concurrently, anchored to that domain
             so reviews, news, and social all reference the same company.

This prevents cross-company contamination: searching "Apple reviews" could
return results for Apple Records or a local shop; "apple.com reviews" cannot.

Signal registry:
  1. Website Credibility  — domain age, SSL, contact info (Ma et al., 2009)
  2. Customer Reviews     — rating + volume across platforms (Luca, HBS 2016)
  3. Adverse Media        — fraud/lawsuit/regulatory mentions (FATF AML guidelines)
  4. Social Presence      — active accounts signal operational legitimacy
  5. Stock Listing        — publicly traded = SEC-audited legitimacy

Adding a new signal:
  1. Create signals/your_signal.py — subclass BaseSignal, implement collect()
  2. Add to PHASE_2_SIGNALS below
  3. Add a formatter in services/formatter.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.schemas.response import SignalResult
from app.services.signals.website import WebsiteSignal
from app.services.signals.reviews import ReviewsSignal
from app.services.signals.adverse_media import AdverseMediaSignal
from app.services.signals.social import SocialSignal
from app.services.signals.stock import StockSignal
from app.services.synthesizer import synthesize_signals

PHASE_2_SIGNALS: list[type] = [
    ReviewsSignal,
    AdverseMediaSignal,
    SocialSignal,
    StockSignal,
]


def _extract_domain(signal: SignalResult) -> str | None:
    """Pull the root domain from the website signal's sources list."""
    for url in (signal.sources or []):
        host = urlparse(url).hostname
        if host:
            # strip www. prefix
            return host.replace("www.", "")
    return None


async def run_analysis(
    business_name: str,
    location:      str | None,
    extra_context: str | None,
) -> dict:
    """
    Phase 1: run WebsiteSignal to discover the canonical domain.
    Phase 2: run all other signals concurrently, passing the domain
             as an anchor so they reference the correct company.
    """
    signals: dict[str, SignalResult] = {}

    # phase 1 website
    try:
        website_result = await WebsiteSignal().collect(business_name, location)
    except Exception as exc:
        website_result = SignalResult(
            name="website", status="error",
            summary=f"Signal collection failed: {str(exc)}",
            sources=[],
        )
    signals["website"] = website_result

    # Extract canonical domain to anchor downstream queries
    canonical_domain = _extract_domain(website_result)

    # phase 2 all other signals concurrently
    collectors = [cls() for cls in PHASE_2_SIGNALS]
    results = await asyncio.gather(
        *[c.collect(business_name, location, canonical_domain) for c in collectors],
        return_exceptions=True,
    )
    for collector, result in zip(collectors, results):
        if isinstance(result, Exception):
            signals[collector.name] = SignalResult(
                name=collector.name, status="error",
                summary=f"Signal collection failed: {str(result)}",
                sources=[],
            )
        else:
            signals[collector.name] = result

    synthesis = await synthesize_signals(business_name, location, extra_context, signals)
    return {
        "signals":      {name: sig.model_dump() for name, sig in signals.items()},
        "synthesis":    synthesis,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }