"""
formatter.py — translates internal SignalResult data into the DossierReport
shape the frontend expects. This is the ONLY file that knows the frontend contract.
Adding a new signal = add one entry to SIGNAL_FORMATTERS. Nothing else changes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

VERDICT_MAP = {
    "LIKELY_LEGIT": "Likely Legitimate",
    "UNCERTAIN":    "Uncertain",
    "RED_FLAGS":    "Potential Risk",
}


def _status(score: float | None) -> str:
    if score is None:
        return "neutral"
    if score >= 60:
        return "positive"
    if score >= 40:
        return "neutral"
    return "negative"

# per-signal formatters

def _fmt_website(signal: dict) -> dict:
    d  = signal.get("details") or {}
    sc = d.get("scoring") or {}
    findings = []

    age_years = sc.get("domain_age_years")
    if age_years is not None:
        yr = int(age_years)
        registered = (d.get("whois") or {}).get("created")
        reg_str = f" (registered {registered[:4]})" if registered else ""
        findings.append({
            "label": "Domain Age",
            "value": f"{yr} year{'s' if yr != 1 else ''}{reg_str}",
            "status": "positive" if yr >= 2 else ("neutral" if yr >= 1 else "negative"),
        })

    https = sc.get("https_enabled")
    if https is not None:
        findings.append({
            "label": "HTTPS",
            "value": "Enabled" if https else "Not enabled",
            "status": "positive" if https else "negative",
        })

    contact = sc.get("contact_info_present")
    if contact is not None:
        findings.append({
            "label": "Contact Info",
            "value": "Phone, email, or address detected" if contact else "No contact info found",
            "status": "positive" if contact else "neutral",
        })

    # Website URL as a clickable finding
    website_url = d.get("url")
    if website_url:
        findings.append({
            "label": "Website",
            "value": website_url,
            "status": "positive" if sc.get("https_enabled") else "neutral",
        })

    if not findings:
        findings.append({"label": "Status", "value": signal.get("summary", "No data"), "status": _status(signal.get("score"))})

    score = signal.get("score") or 50
    if score >= 65:
        interp = "Website shows strong indicators of a legitimate, established business."
    elif score >= 40:
        interp = "Website has some legitimacy indicators but gaps exist."
    else:
        interp = "Website shows limited or missing legitimacy indicators."

    missing, negative = [], []
    if https is False:
        negative.append("Website missing HTTPS/SSL")
    if contact is False:
        missing.append("No contact information detected on website")
    if age_years is not None and age_years < 1:
        negative.append("Very new domain (less than 1 year old)")

    return {
        "title": "Website Credibility",
        "findings": findings,
        "interpretation": interp,
        "source": "WHOIS + website scan",
        "sources": [website_url] if website_url else [],
        "missing": missing,
        "negative": negative,
    }


def _fmt_reviews(signal: dict) -> dict:
    d  = signal.get("details") or {}
    sc = d.get("scoring") or {}
    findings = []

    rating = sc.get("avg_rating")
    if rating is not None:
        findings.append({
            "label": "Average Rating",
            "value": f"{rating:.1f} / 5.0",
            "status": "positive" if rating >= 3.5 else ("neutral" if rating >= 2.5 else "negative"),
        })

    count = sc.get("review_count")
    if count is not None:
        findings.append({
            "label": "Total Reviews",
            "value": str(count),
            "status": "positive" if count >= 20 else ("neutral" if count >= 5 else "negative"),
        })

    # Add review platform links as findings
    results = d.get("results") or []
    review_sources = []
    for r in results[:3]:
        link = r.get("link", "")
        if link:
            review_sources.append(link)
            findings.append({
                "label": "Review Source",
                "value": link,
                "status": "positive",
            })

    if not findings:
        findings.append({"label": "Status", "value": signal.get("summary", "No reviews found"), "status": _status(signal.get("score"))})

    score = signal.get("score") or 50
    if score >= 65:
        interp = "Consistent positive reviews with recent activity suggest genuine customer engagement."
    elif score >= 40:
        interp = "Mixed or limited review presence across platforms."
    else:
        interp = "Low ratings or very few reviews detected — may warrant further investigation."

    missing, negative = [], []
    if signal.get("status") == "not_found":
        missing.append("No review platforms found (Yelp, BBB, Trustpilot)")
    if rating is not None and rating < 2.5:
        negative.append(f"Low average rating ({rating:.1f}/5.0)")

    return {
        "title": "Customer Reviews",
        "findings": findings,
        "interpretation": interp,
        "source": "Serper → Yelp / BBB / Trustpilot",
        "sources": review_sources,
        "missing": missing,
        "negative": negative,
    }


def _fmt_adverse(signal: dict) -> dict:
    d = signal.get("details") or {}
    findings = []
    article_sources = []

    guardian_available  = d.get("guardian_available", False)
    guardian_articles   = d.get("guardian_articles") or []
    newsapi_available   = d.get("newsapi_available", False)
    newsapi_articles    = d.get("newsapi_articles") or []
    adverse_count       = d.get("adverse_count", 0)
    total               = d.get("total_results", 0)

    # guardian recent coverage
    if not guardian_available:
        findings.append({
            "label": "Recent Coverage",
            "value": "Add GUARDIAN_API_KEY to .env to enable",
            "status": "neutral",
        })
    elif not guardian_articles:
        findings.append({
            "label": "Recent Coverage",
            "value": "No recent Guardian coverage found",
            "status": "neutral",
        })
    else:
        for a in guardian_articles:
            url  = a.get("url", "")
            date = (a.get("publishedAt") or "")[:10]
            if url:
                article_sources.append(url)
            findings.append({
                "label": f"Guardian{' · ' + date if date else ''}",
                "value": url if url else a.get("title", ""),
                "status": "positive",
            })

    # newsapi adverse screening
    if not newsapi_available:
        findings.append({
            "label": "Adverse Screening",
            "value": "Add NEWS_API_KEY to .env to enable",
            "status": "neutral",
        })
    elif not newsapi_articles and total == 0:
        findings.append({
            "label": "Adverse Screening",
            "value": "No articles found — name may not be indexed by NewsAPI",
            "status": "neutral",
        })
    else:
        findings.append({
            "label": "Articles Scanned",
            "value": str(total),
            "status": "positive",
        })
        findings.append({
            "label": "Adverse Mentions",
            "value": (
                "None detected ✓"
                if adverse_count == 0
                else f"{adverse_count} article(s) flagged (fraud, lawsuits, regulatory actions)"
            ),
            "status": "positive" if adverse_count == 0 else ("neutral" if adverse_count <= 1 else "negative"),
        })
        for a in newsapi_articles:
            if a.get("is_adverse") and a.get("url"):
                url = a["url"]
                article_sources.append(url)
                findings.append({
                    "label": f"⚠ {a.get('source', 'Source')}",
                    "value": url,
                    "status": "negative",
                })

    # interpretation
    if adverse_count == 0 and newsapi_available:
        if total == 0:
            interp = "No news found via NewsAPI — this doesn't indicate risk, but coverage could not be verified. Guardian articles (if shown) confirm public presence."
        else:
            interp = f"Scanned {total} recent article(s) via NewsAPI — no adverse coverage detected."
    elif adverse_count == 1:
        interp = "One adverse article found — review manually to assess severity."
    elif adverse_count > 1:
        interp = f"{adverse_count} adverse articles detected. Significant risk indicators present."
    else:
        interp = "Media screening incomplete — configure API keys for full coverage."

    missing, negative = [], []
    for a in newsapi_articles:
        if a.get("is_adverse") and a.get("title"):
            negative.append(a["title"][:80])
    if not guardian_available and not newsapi_available:
        missing.append("No media APIs configured")

    return {
        "title": "Media & News",
        "findings": findings,
        "interpretation": interp,
        "source": "The Guardian API + NewsAPI",
        "sources": list(dict.fromkeys(article_sources)),
        "missing": missing,
        "negative": negative,
    }


def _fmt_social(signal: dict) -> dict:
    d = signal.get("details") or {}
    platforms = d.get("platforms_found") or []
    raw_srcs = signal.get("sources") or []
    findings= []

    platform_labels = {
        "linkedin":  "LinkedIn",
        "facebook":  "Facebook",
        "instagram": "Instagram",
        "twitter":   "Twitter/X",
        "youtube":   "YouTube",
    }

    found_set = set(platforms)

    # Map platform → its URL from sources list
    platform_urls: dict[str, str] = {}
    for url in raw_srcs:
        for p in platform_labels:
            if p in url or (p == "twitter" and "x.com" in url):
                platform_urls[p] = url

    for p in ["linkedin", "facebook", "instagram", "twitter", "youtube"]:
        label = platform_labels.get(p, p.title())
        if p in found_set:
            url = platform_urls.get(p, "")
            findings.append({
                "label": label,
                "value": url if url else "Found",
                "status": "positive",
            })
        elif p in ("linkedin", "instagram"):
            findings.append({"label": label, "value": "Not found", "status": "neutral"})

    if not findings:
        findings.append({"label": "Social Presence", "value": "No accounts detected", "status": "neutral"})

    n = len(platforms)
    if n >= 3:
        interp = f"Active presence on {n} platforms. Strong operational social signals."
    elif n >= 1:
        interp = f"Found on {n} platform(s): {', '.join(platforms)}. Missing platforms are a minor gap."
    else:
        interp = "No social accounts detected. This may be normal for B2B or established businesses."

    missing  = [f"{platform_labels.get(p, p.title())}: Not found" for p in ("linkedin", "instagram") if p not in found_set]
    negative = []

    return {
        "title": "Social Presence",
        "findings": findings,
        "interpretation": interp,
        "source": "Serper → public social profiles",
        "sources": list(platform_urls.values()),
        "missing": missing,
        "negative": negative,
    }


# registry
SIGNAL_FORMATTERS = {
    "website":       _fmt_website,
    "reviews":       _fmt_reviews,
    "adverse_media": _fmt_adverse,
    "social_media":  _fmt_social,
}
# Stock is intentionally excluded — it renders as a header badge, not a signal card
SIGNAL_ORDER = ["website", "reviews", "adverse_media", "social_media"]



def build_dossier_report(
    run_id: int,
    business_name: str,
    location: str | None,
    created_at: datetime,
    signals_raw: dict[str, Any],
    synthesis: dict,
) -> dict:
    formatted_signals = []
    all_missing: list[str] = []
    all_negative:  list[str] = []
    all_sources:   list[str] = []

    for key in SIGNAL_ORDER:
        signal = signals_raw.get(key)
        if not signal:
            continue
        formatter = SIGNAL_FORMATTERS.get(key)
        if not formatter:
            continue

        result        = formatter(signal)
        score         = signal.get("score") or 50
        signal_status = _status(score) if not signal.get("is_mocked") else "neutral"

        formatted_signals.append({
            "title":          result["title"],
            "status":         signal_status,
            "findings":       result["findings"],
            "interpretation": result["interpretation"],
            "source":         result["source"],
            "sources":        result.get("sources", []),
        })

        all_missing.extend(result.get("missing", []))
        all_negative.extend(result.get("negative", []))

        for url in result.get("sources", []):
            if url and url.startswith("http") and url not in all_sources:
                all_sources.append(url)

    # Global sources footer
    sources = list(dict.fromkeys(all_sources))

    # Verdict + score
    raw_verdict     = synthesis.get("verdict", "UNCERTAIN")
    display_verdict = VERDICT_MAP.get(raw_verdict, "Uncertain")
    confidence      = synthesis.get("confidence_score") or 50
    display_score   = round(confidence / 10, 1)

    # Reasoning
    reasoning = synthesis.get("key_positives") or []
    notes     = synthesis.get("analyst_notes", "")
    if notes and "Fallback scoring" not in notes and "Error:" not in notes:
        reasoning = reasoning + [notes]
    if not reasoning:
        summary = synthesis.get("verdict_summary", "")
        reasoning = [summary] if summary else ["Analysis complete. Configure API keys for detailed findings."]

    # stock ticker badge data
    stock_raw    = signals_raw.get("stock") or {}
    stock_detail = stock_raw.get("details") or {}
    ticker_info  = None
    if stock_detail.get("listed") and stock_detail.get("ticker"):
        ticker_info = {
            "symbol":   stock_detail["ticker"],
            "exchange": stock_detail.get("exchange", ""),
            "url":      (stock_raw.get("sources") or [None])[0],
        }

    return {
        "id":               str(run_id),
        "businessName":     business_name,
        "location":         location or "Not specified",
        "timestamp":        created_at.isoformat().replace("+00:00", "Z") if created_at else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "credibilityScore": display_score,
        "verdict":          display_verdict,
        "reasoning":        reasoning[:6],
        "signals":          formatted_signals,
        "missingSignals":   list(dict.fromkeys(all_missing))[:8],
        "negativeSignals":  list(dict.fromkeys(all_negative))[:8],
        "sources":          sources,
        "nameFlag":         synthesis.get("name_flag"),
        "ticker":           ticker_info,
    }