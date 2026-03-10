"""
signals/social.py

Social media presence signal: LinkedIn, Facebook, Instagram, Twitter/X, YouTube.

Scoring:
  S_social = max(0.4, RawScore)
  Floor of 0.4 means absence is neutral, not a red flag.
  A 50-year-old B2B manufacturer with no Instagram is not suspicious.
"""
from __future__ import annotations

from app.schemas.response import SignalResult
from app.services.signals.base import BaseSignal
from app.services.signals.google_client import search_google

PLATFORMS = {
    "linkedin":  "site:linkedin.com/company",
    "facebook":  "site:facebook.com",
    "instagram": "site:instagram.com",
    "twitter":   "site:twitter.com OR site:x.com",
    "youtube":   "site:youtube.com",
}


class SocialSignal(BaseSignal):
    name = "social_media"

    async def collect(self, business_name: str, location: str | None, canonical_domain: str | None = None) -> SignalResult:
        # location not used for social search — intentional
        try:
            return await self._run(business_name)
        except Exception as exc:
            return self._error_result(exc)

    async def _run(self, business_name: str) -> SignalResult:
        found_platforms: list[str] = []
        sources: list[str] = []

        for platform, site_query in PLATFORMS.items():
            try:
                items = await search_google(f'"{business_name}" {site_query}', num=2)
                if items:
                    found_platforms.append(platform)
                    sources.extend(i.get("link", "") for i in items[:1])
            except Exception:
                pass

        if not found_platforms and not sources:
            return SignalResult(
                name=self.name,
                status="not_found",
                score=40,
                summary="Social media search requires Google Custom Search API keys.",
                sources=[],
                is_mocked=True,
                details={
                    "note": "Configure SERPER_API_KEY in .env to enable.",
                    "scoring": {"accounts_found": 0, "normalized_score": 0.4, "note": "neutral floor applied"},
                },
            )

        from app.services.scoring import compute_social_score
        s = compute_social_score(
            accounts_found=len(found_platforms),
            activity_score=0.5,   # unknown recency via CSE → neutral
            follower_count=None,
        )

        return SignalResult(
            name=self.name,
            status="found" if found_platforms else "not_found",
            score=round(s * 100),
            summary=f"Found presence on {len(found_platforms)} platform(s): {', '.join(found_platforms) or 'none detected'}.",
            details={
                "platforms_found": found_platforms,
                "scoring": {
                    "accounts_found":   len(found_platforms),
                    "activity_score":   0.5,
                    "follower_count":   None,
                    "normalized_score": round(s, 3),
                    "note": "activity and follower data unavailable via CSE; production APIs would provide these",
                },
            },
            sources=sources[:5],
        )
