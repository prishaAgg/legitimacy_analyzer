"""
signals/stock.py
Public listing signal via Yahoo Finance search API (direct HTTP).

Calls Yahoo's internal search endpoint directly with httpx, which gives
full control over headers and avoids the Docker-blocking issue with yfinance.

Fuzzy matching via difflib — threshold 60% to avoid false positives.
No API key required.

Limitation: Yahoo's search endpoint is unofficial. For production use
FMP (financialmodelingprep.com) or Polygon.io.
"""
from __future__ import annotations

import asyncio
import httpx
from difflib import SequenceMatcher

from app.schemas.response import SignalResult
from app.services.signals.base import BaseSignal

YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

MATCH_THRESHOLD = 0.60

MAJOR_EXCHANGES = {
    "NYQ", "NMS", "NGM", "NCM",
    "NYSE", "NASDAQ",
    "LSE", "LSX", "TSX", "TOR",
    "ASX", "XETRA", "GER",
    "HKG", "TYO", "NSE", "BSE",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _best_match(query: str, quotes: list[dict]) -> tuple[dict | None, float]:
    best_quote, best_score = None, 0.0
    for q in quotes:
        # Only consider equities, not ETFs/indices/crypto
        if q.get("quoteType") not in ("EQUITY", "ETF"):
            continue
        name = q.get("longname") or q.get("shortname") or ""
        if not name:
            continue
        score = _similarity(query, name)
        if score > best_score:
            best_score = score
            best_quote = q
    return best_quote, best_score


class StockSignal(BaseSignal):
    name = "stock"

    async def collect(self, business_name: str, location: str | None, canonical_domain: str | None = None) -> SignalResult:
        try:
            return await self._run(business_name)
        except Exception as exc:
            return self._error_result(exc)

    async def _run(self, business_name: str) -> SignalResult:
        params = {
            "q":            business_name,
            "quotesCount":  8,
            "newsCount":    0,
            "listsCount":   0,
            "lang":         "en-US",
        }

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
                resp = await client.get(YAHOO_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return SignalResult(
                name=self.name, status="not_found", score=None,
                summary=f"Stock lookup unavailable: {str(e)}",
                sources=[],
                details={"listed": False, "ticker": None, "exchange": None},
            )

        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])

        if not quotes:
            return SignalResult(
                name=self.name, status="not_found", score=None,
                summary=f"'{business_name}' does not appear to be publicly listed.",
                sources=[],
                details={"listed": False, "ticker": None, "exchange": None},
            )

        best, score = _best_match(business_name, quotes)

        if best is None or score < MATCH_THRESHOLD:
            best_name = (best or {}).get("longname") or (best or {}).get("shortname")
            return SignalResult(
                name=self.name, status="not_found", score=None,
                summary=f"No confident stock match for '{business_name}' (best: {score:.0%}).",
                sources=[],
                details={
                    "listed": False, "ticker": None, "exchange": None,
                    "best_match": best_name,
                    "confidence": round(score, 3),
                },
            )

        ticker   = best.get("symbol", "")
        exchange = (best.get("exchange") or best.get("fullExchangeName") or "").upper()
        name     = best.get("longname") or best.get("shortname") or business_name

        return SignalResult(
            name=self.name, status="found", score=None,
            summary=f"Listed on {exchange} as {ticker} ({name}). Match confidence: {score:.0%}.",
            sources=[f"https://finance.yahoo.com/quote/{ticker}"],
            details={
                "listed":            True,
                "ticker":            ticker,
                "exchange":          exchange,
                "full_name":         name,
                "confidence":        round(score, 3),
                "is_major_exchange": exchange in MAJOR_EXCHANGES,
            },
        )