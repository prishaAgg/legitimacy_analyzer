"""
signals/google_client.py

Thin wrapper around Serper.dev — real Google Search results via a clean API.
All signal collectors that need web search import from here.

Free tier: 2,500 queries (no credit card required).
Sign up:   https://serper.dev
Docs:      https://serper.dev/playground

Serper returns the same structure as real Google Search (organic results,
knowledge graph, answer box) — much better than Google Custom Search API.
Response items include: title, link, snippet, (sometimes) sitelinks.

To swap search providers in future, only this file needs to change.
"""
from __future__ import annotations

import httpx
from app.config import get_settings

SERPER_URL = "https://google.serper.dev/search"


async def search_google(query: str, num: int = 5) -> list[dict]:
    """
    Run a Google search via Serper.dev. Returns a list of result dicts,
    each with keys: title, link, snippet.
    Returns [] silently if SERPER_API_KEY is not configured.
    """
    settings = get_settings()
    if not settings.serper_api_key:
        return []

    payload = {"q": query, "num": num}
    headers = {
        "X-API-KEY":    settings.serper_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(SERPER_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Serper returns organic results under "organic" key.
    # Each item: { title, link, snippet, position, ... }
    return data.get("organic", [])