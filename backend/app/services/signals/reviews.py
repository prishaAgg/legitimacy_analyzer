"""
signals/reviews.py
Customer reviews signal: rating + volume via Google Custom Search.
Searches Yelp, Trustpilot, Google Maps (excludes BBB — complaint-focused,
not a reliable rating source).

Scoring (updated):
  S_reviews = 0.4 × RatingScore + 0.6 × VolumeScore
  RatingScore = avg_rating / 5  (0 if no rating found — not penalized heavily)
  VolumeScore = min(review_count / 10000, 1)  saturates at 10,000 reviews

Volume weighted more heavily than rating because:
  - Legitimacy ≠ quality. 50k reviews = verifiably real business.
  - Large institutions have structurally low ratings (unhappy customers
    review more). A bank with 2/5 stars and 100k reviews is still legitimate.

Research basis: Luca (HBS 2016) — review volume as business legitimacy proxy.
"""
from __future__ import annotations

import re
from app.config import get_settings
from app.schemas.response import SignalResult
from app.services.signals.base import BaseSignal
from app.services.signals.google_client import search_google

# BBB excluded — its pages surface complaint counts, not star ratings,
# which breaks avg_rating extraction and inflates review_count incorrectly.
REVIEW_SITES = "site:yelp.com OR site:trustpilot.com OR site:google.com/maps"


class ReviewsSignal(BaseSignal):
    name = "reviews"

    async def collect(self, business_name: str, location: str | None, canonical_domain: str | None = None) -> SignalResult:
        try:
            return await self._run(business_name, location, canonical_domain)
        except Exception as exc:
            return self._error_result(exc)

    async def _run(self, business_name: str, location: str | None, canonical_domain: str | None = None) -> SignalResult:
        query = f'"{business_name}" reviews {REVIEW_SITES}'
        if location:
            query += f" {location}"

        items = await search_google(query, num=5)

        # Fallback: broader query without site restriction
        if not items:
            items = await search_google(f"{business_name} customer reviews ratings", num=5)

        if not items:
            return SignalResult(
                name=self.name,
                status="not_found",
                score=50,
                summary="No review sources found. This may indicate limited online presence.",
                sources=[],
                is_mocked=not bool(get_settings().serper_api_key),
            )

        sources  = [item.get("link", "") for item in items]
        titles   = [item.get("title", "") for item in items]
        snippets = [item.get("snippet", "") for item in items]
        combined = " ".join(snippets + titles)

        # Extract star ratings — look for patterns like "4.2 out of 5", "3.8 stars", "4.5/5"
        ratings = re.findall(
            r'\b([0-4]\.\d|[1-5])\s*(?:out of 5|stars?|/5|\u2605)',
            combined,
            re.IGNORECASE,
        )
        avg_rating = None
        if ratings:
            try:
                vals = [float(r) for r in ratings if 0 < float(r) <= 5]
                if vals:
                    avg_rating = sum(vals) / len(vals)
            except Exception:
                pass

        # Extract review counts — look for "74,407 reviews", "1.2K reviews"
        count_matches = re.findall(
            r'([\d,]+(?:\.\d+)?[kKmM]?)\s+reviews?',
            combined,
            re.IGNORECASE,
        )
        review_count = None
        if count_matches:
            try:
                counts = []
                for c in count_matches:
                    c = c.replace(",", "").strip()
                    if c.lower().endswith("k"):
                        counts.append(int(float(c[:-1]) * 1000))
                    elif c.lower().endswith("m"):
                        counts.append(int(float(c[:-1]) * 1_000_000))
                    else:
                        counts.append(int(float(c)))
                review_count = max(counts)
            except Exception:
                pass

        from app.services.scoring import compute_review_score
        s = compute_review_score(avg_rating, review_count)

        rating_str = f" Average rating ~{avg_rating:.1f}/5." if avg_rating else ""
        count_str  = f" {review_count:,} total reviews." if review_count else ""

        return SignalResult(
            name=self.name,
            status="found",
            score=round(s * 100),
            summary=f"Found review mentions across {len(items)} sources.{rating_str}{count_str}",
            details={
                "results": [
                    {"title": t, "link": lnk, "snippet": sn}
                    for t, lnk, sn in zip(titles, sources, snippets)
                ],
                "scoring": {
                    "avg_rating":       round(avg_rating, 2) if avg_rating else None,
                    "review_count":     review_count,
                    "normalized_score": round(s, 3),
                },
            },
            sources=sources[:5],
        )