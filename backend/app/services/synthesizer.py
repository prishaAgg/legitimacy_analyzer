"""
Claude AI synthesis service.
Takes all collected signals and produces a structured analyst verdict.
"""
from __future__ import annotations

import json
import anthropic
from app.config import get_settings
from app.schemas.response import SignalResult

VERDICT_PROMPT = """You are an expert business due-diligence analyst. You have been given automated signal data about a business. Your job is to synthesize this into a clear analyst report.

Business: {business_name}
Location: {location}
Context: {extra_context}

## Signal Data
{signals_json}

## Task
Based on the signals above, produce a JSON response with this exact structure:
{{
  "confidence_score": <number 0-100>,
  "verdict": "<LIKELY_LEGIT | UNCERTAIN | RED_FLAGS>",
  "verdict_summary": "<2-3 sentence plain-English summary an analyst can act on>",
  "key_positives": ["<finding>", ...],
  "key_concerns": ["<concern>", ...],
  "data_gaps": ["<what we couldn't find>", ...],
  "analyst_notes": "<1-2 sentences of nuanced professional judgment>",
  "name_flag": "<null, or a short note if the business name looks misspelled or ambiguous>"
}}

Scoring guide:
- 75-100: Strong legitimate signals, minimal concerns → LIKELY_LEGIT
- 45-74: Mixed signals, some gaps or minor concerns → UNCERTAIN
- 0-44: Multiple red flags, adverse media, or no verifiable presence → RED_FLAGS

Important rules:
- "No information found" is DIFFERENT from "negative information found"
- A brand new business with no history is UNCERTAIN, not RED_FLAGS
- Mocked/unavailable signals should be noted as gaps, not negatives
- Weight adverse media heavily if present
- If location is provided, use it to disambiguate businesses with common names (e.g. "Wells Fargo" with location "San Francisco" vs a local store with the same name)
- If the business name appears to be misspelled or nonsensical, set name_flag to a short note like "Possible misspelling — did you mean X?"
- For large well-known institutions (universities, banks, major corporations), weight website and adverse media more heavily than reviews since they may not appear on Yelp/BBB

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON."""


async def synthesize_signals(
    business_name: str,
    location: str | None,
    extra_context: str | None,
    signals: dict[str, SignalResult],
) -> dict:
    """Call Claude to synthesize all signals into a verdict."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        return _fallback_synthesis(signals)

    signals_summary = {}
    for name, signal in signals.items():
        signals_summary[name] = {
            "status":        signal.status,
            "score":         signal.score,
            "summary":       signal.summary,
            "is_mocked":     signal.is_mocked,
            "sources_count": len(signal.sources),
        }

    prompt = VERDICT_PROMPT.format(
        business_name=business_name,
        location=location or "Not specified",
        extra_context=extra_context or "None",
        signals_json=json.dumps(signals_summary, indent=2),
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0,   # deterministic output — reduces score variance
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    except Exception as e:
        return _fallback_synthesis(signals, error=str(e))


def _fallback_synthesis(signals: dict[str, SignalResult], error: str = "") -> dict:
    """Rule-based fallback when Claude API is unavailable."""
    from app.services.scoring import compute_final_score

    def get_s(name):
        sig = signals.get(name)
        if sig and sig.score is not None:
            return sig.score / 100.0
        return 0.5

    # Check if stock signal confirmed public listing
    stock_sig = signals.get("stock")
    publicly_listed = bool(
        stock_sig and
        not stock_sig.is_mocked and
        (stock_sig.details or {}).get("listed")
    )

    result = compute_final_score(
        s_website=get_s("website"),
        s_reviews=get_s("reviews"),
        s_adverse=get_s("adverse_media"),
        s_social=get_s("social_media"),
        publicly_listed=publicly_listed,
    )

    positives = [s.summary for s in signals.values() if (s.score or 0) >= 65]
    concerns  = [s.summary for s in signals.values() if (s.score or 0) < 45]
    gaps      = [s.name for s in signals.values() if s.is_mocked]

    return {
        "confidence_score": result["confidence_score"],
        "verdict":          result["verdict"],
        "verdict_summary":  f"Rule-based score: {result['display_score']}/10 "
                            f"({result['verdict'].replace('_', ' ')}). "
                            f"{len(positives)} positive signal(s), {len(concerns)} concern(s).",
        "key_positives":    positives[:3],
        "key_concerns":     concerns[:3],
        "data_gaps":        gaps,
        "analyst_notes":    "Fallback scoring active — configure ANTHROPIC_API_KEY for AI synthesis."
                            + (f" Error: {error}" if error else ""),
        "name_flag":        None,
        "score_components": result["components"],
    }