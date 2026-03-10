"""
tests/test_formatter.py
=======================
Unit tests for the DossierReport formatter.
These verify the frontend contract is always satisfied — no I/O.

Run with:  pytest tests/test_formatter.py -v
"""
from datetime import datetime, timezone
import pytest
from app.services.formatter import build_dossier_report

# fixtures

MOCK_SIGNALS = {
    "website": {
        "name": "website", "status": "found", "score": 80, "is_mocked": False,
        "summary": "Website looks good.", "sources": ["https://example.com"],
        "details": {
            "scoring": {
                "domain_age_years": 5.0, "https_enabled": True,
                "contact_info_present": True, "normalized_score": 0.8,
            },
            "whois": {"created": "2019-01-01"},
        },
    },
    "reviews": {
        "name": "reviews", "status": "found", "score": 70, "is_mocked": False,
        "summary": "Good reviews.", "sources": ["https://yelp.com/biz/example"],
        "details": {"scoring": {"avg_rating": 4.2, "review_count": 45, "normalized_score": 0.72}},
    },
    "adverse_media": {
        "name": "adverse_media", "status": "found", "score": 100, "is_mocked": False,
        "summary": "No adverse coverage.", "sources": [],
        "details": {"total_results": 0, "adverse_count": 0, "scoring": {"negative_article_count": 0}},
    },
    "social_media": {
        "name": "social_media", "status": "found", "score": 60, "is_mocked": False,
        "summary": "Found on 2 platforms.", "sources": [],
        "details": {"platforms_found": ["linkedin", "instagram"]},
    },
}

MOCK_SYNTHESIS = {
    "confidence_score": 75,
    "verdict": "LIKELY_LEGIT",
    "verdict_summary": "Business appears legitimate.",
    "key_positives": ["Established domain", "Good reviews"],
    "key_concerns": [],
    "analyst_notes": "Solid signals across the board.",
}

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def build(**overrides):
    kwargs = dict(
        run_id=42,
        business_name="Acme Corp",
        location="New York, NY",
        created_at=NOW,
        signals_raw=MOCK_SIGNALS,
        synthesis=MOCK_SYNTHESIS,
    )
    kwargs.update(overrides)
    return build_dossier_report(**kwargs)


# tests

class TestRequiredFields:
    def test_has_all_top_level_fields(self):
        report = build()
        required = ["id", "businessName", "location", "timestamp",
                    "credibilityScore", "verdict", "reasoning",
                    "signals", "missingSignals", "negativeSignals", "sources"]
        for field in required:
            assert field in report, f"Missing field: {field}"

    def test_id_is_string(self):
        assert build()["id"] == "42"

    def test_business_name_preserved(self):
        assert build()["businessName"] == "Acme Corp"

    def test_location_preserved(self):
        assert build()["location"] == "New York, NY"

    def test_location_defaults_to_not_specified(self):
        assert build(location=None)["location"] == "Not specified"

    def test_timestamp_ends_with_z(self):
        assert build()["timestamp"].endswith("Z")


class TestScoreAndVerdict:
    def test_credibility_score_is_float(self):
        score = build()["credibilityScore"]
        assert isinstance(score, float)

    def test_credibility_score_in_range(self):
        score = build()["credibilityScore"]
        assert 0 <= score <= 10

    def test_verdict_likely_legitimate(self):
        assert build()["verdict"] == "Likely Legitimate"

    def test_verdict_uncertain(self):
        s = dict(MOCK_SYNTHESIS, verdict="UNCERTAIN", confidence_score=55)
        assert build(synthesis=s)["verdict"] == "Uncertain"

    def test_verdict_potential_risk(self):
        s = dict(MOCK_SYNTHESIS, verdict="RED_FLAGS", confidence_score=30)
        assert build(synthesis=s)["verdict"] == "Potential Risk"


class TestSignals:
    def test_four_signals_returned(self):
        assert len(build()["signals"]) == 4

    def test_each_signal_has_required_keys(self):
        for signal in build()["signals"]:
            for key in ["title", "status", "findings", "interpretation", "source"]:
                assert key in signal, f"Signal missing key: {key}"

    def test_signal_status_valid_values(self):
        for signal in build()["signals"]:
            assert signal["status"] in ("positive", "neutral", "negative")

    def test_findings_are_list(self):
        for signal in build()["signals"]:
            assert isinstance(signal["findings"], list)


class TestReasoning:
    def test_reasoning_is_list_of_strings(self):
        reasoning = build()["reasoning"]
        assert isinstance(reasoning, list)
        assert all(isinstance(r, str) for r in reasoning)

    def test_reasoning_includes_analyst_notes(self):
        reasoning = build()["reasoning"]
        assert any("Solid signals" in r for r in reasoning)


class TestSources:
    def test_sources_is_list(self):
        assert isinstance(build()["sources"], list)

    def test_sources_not_empty(self):
        assert len(build()["sources"]) > 0
