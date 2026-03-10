"""
signals/adverse_media.py
Two-part media signal:

  1. Guardian API  — top 3 most recent articles from a credible outlet.
                     Shows the business is real and newsworthy.
                     Free: 500 req/day. Sign up at open-platform.theguardian.com

  2. NewsAPI       — adverse media screening across broader sources.
                     Flags articles mentioning fraud, lawsuits, regulatory actions.
                     Free: 100 req/day. Sign up at newsapi.org

Both run concurrently. Guardian result is purely informational (not scored).
Scoring is based on NewsAPI adverse count only via exponential decay:
  S_adverse = exp(-0.5 × k)   where k = adverse article count
"""
from __future__ import annotations

import asyncio
import httpx
from datetime import datetime, timedelta

from app.schemas.response import SignalResult
from app.services.signals.base import BaseSignal
from app.config import get_settings

NEWS_API_URL    = "https://newsapi.org/v2/everything"
GUARDIAN_API_URL = "https://content.guardianapis.com/search"

ADVERSE_KEYWORDS = [
    "fraud", "lawsuit", "scam", "complaint", "investigation",
    "fine", "penalty", "bankrupt", "shutdown", "violation",
    "arrested", "indicted", "regulatory", "breach", "recall",
]


class AdverseMediaSignal(BaseSignal):
    name = "adverse_media"

    async def collect(self, business_name: str, location: str | None, canonical_domain: str | None = None) -> SignalResult:
        try:
            return await self._run(business_name, canonical_domain)
        except Exception as exc:
            return self._error_result(exc)

    async def _run(self, business_name: str, canonical_domain: str | None = None) -> SignalResult:
        settings = get_settings()

        # Run Guardian + NewsAPI concurrently
        guardian_task = self._fetch_guardian(business_name, settings)
        newsapi_task  = self._fetch_newsapi(business_name, settings)

        guardian_articles, (newsapi_articles, total) = await asyncio.gather(
            guardian_task, newsapi_task
        )

        from app.services.scoring import compute_adverse_score

        # newsapi adverse classification
        adverse, neutral = [], []
        for article in newsapi_articles:
            text = (
                (article.get("title") or "") + " " +
                (article.get("description") or "") + " " +
                (article.get("content") or "")
            ).lower()
            (adverse if any(kw in text for kw in ADVERSE_KEYWORDS) else neutral).append(article)

        k = len(adverse)
        s = compute_adverse_score(k)

        # build details dict
        newsapi_available = bool(settings.news_api_key)
        guardian_available = bool(settings.guardian_api_key)

        all_newsapi = adverse + neutral
        newsapi_sources = [a.get("url", "") for a in all_newsapi[:3] if a.get("url")]

        # Summary line
        if not newsapi_available:
            adverse_summary = "NewsAPI not configured — adverse screening unavailable."
        elif not newsapi_articles:
            adverse_summary = "No articles found via NewsAPI in past 30 days."
        elif k == 0:
            adverse_summary = f"No adverse coverage in {len(newsapi_articles)} article(s) scanned."
        else:
            adverse_summary = f"⚠ {k} adverse article(s) detected out of {len(newsapi_articles)} scanned."

        guardian_summary = (
            f"{len(guardian_articles)} recent article(s) from The Guardian."
            if guardian_articles else
            ("Guardian API not configured." if not guardian_available else "No Guardian coverage found.")
        )

        return SignalResult(
            name=self.name,
            status="found" if (newsapi_articles or guardian_articles) else "not_found",
            score=round(s * 100),
            is_mocked=not newsapi_available,
            summary=f"{adverse_summary} {guardian_summary}".strip(),
            details={
                # Guardian recent coverage
                "guardian_articles": guardian_articles,
                "guardian_available": guardian_available,
                # NewsAPI adverse screening
                "total_results":  total,
                "adverse_count":  k,
                "newsapi_available": newsapi_available,
                "scoring": {"negative_article_count": k, "normalized_score": round(s, 3)},
                "newsapi_articles": [
                    {
                        "title":       a.get("title"),
                        "url":         a.get("url"),
                        "source":      a.get("source", {}).get("name"),
                        "publishedAt": a.get("publishedAt"),
                        "description": a.get("description"),
                        "is_adverse":  a in adverse,
                    }
                    for a in all_newsapi[:6]
                ],
            },
            sources=(
                [a["url"] for a in guardian_articles if a.get("url")]
                + newsapi_sources
            ),
        )

    # Guardian API

    async def _fetch_guardian(self, business_name: str, settings) -> list[dict]:
        if not settings.guardian_api_key:
            return []
        try:
            params = {
                "q":           f'"{business_name}"',
                "api-key":     settings.guardian_api_key,
                "page-size":   3,
                "order-by":    "newest",
                "show-fields": "headline,trailText,shortUrl",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(GUARDIAN_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = data.get("response", {}).get("results", [])
            name_lower = business_name.lower()
            return [
                {
                    "title":       r.get("webTitle"),
                    "url":         r.get("webUrl"),
                    "publishedAt": r.get("webPublicationDate"),
                    "section":     r.get("sectionName"),
                    "source":      "The Guardian",
                }
                for r in results
                if name_lower in (r.get("webTitle") or "").lower()
            ]
        except Exception:
            return []

    # newsapi

    async def _fetch_newsapi(self, business_name: str, settings) -> tuple[list, int]:
        if not settings.news_api_key:
            return [], 0
        try:
            from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            params = {
                "apiKey":   settings.news_api_key,
                "q":        f'"{business_name}"',
                "from":     from_date,
                "sortBy":   "relevancy",
                "pageSize": 20,
                "language": "en",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(NEWS_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            return data.get("articles", []), data.get("totalResults", 0)
        except Exception:
            return [], 0