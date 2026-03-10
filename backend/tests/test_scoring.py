"""
tests/test_scoring.py
=====================
Unit tests for the credibility scoring model.
These are pure math — no I/O, no API calls, fast.

Run with:  pytest tests/test_scoring.py -v
"""
import math
import pytest
from app.services.scoring import (
    compute_website_score,
    compute_review_score,
    compute_adverse_score,
    compute_social_score,
    compute_final_score,
    W_WEBSITE, W_REVIEWS, W_ADVERSE, W_SOCIAL,
    THRESHOLD_LEGIT, THRESHOLD_UNCERTAIN,
)


class TestWeights:
    def test_weights_sum_to_one(self):
        assert abs(W_WEBSITE + W_REVIEWS + W_ADVERSE + W_SOCIAL - 1.0) < 1e-9


class TestWebsiteScore:
    def test_perfect_score(self):
        s = compute_website_score(domain_age_years=10, https_enabled=True, contact_info_present=True)
        assert s == pytest.approx(1.0)

    def test_new_domain_no_ssl_no_contact(self):
        s = compute_website_score(domain_age_years=0, https_enabled=False, contact_info_present=False)
        assert s == pytest.approx(0.0)

    def test_domain_age_caps_at_5_years(self):
        s_5  = compute_website_score(5,  False, False)
        s_10 = compute_website_score(10, False, False)
        assert s_5 == pytest.approx(s_10)

    def test_unknown_inputs_return_neutral(self):
        s = compute_website_score(None, None, None)
        assert s == pytest.approx(0.5)

    def test_https_only(self):
        s = compute_website_score(domain_age_years=0, https_enabled=True, contact_info_present=False)
        assert s == pytest.approx(0.3)


class TestReviewScore:
    def test_perfect_reviews(self):
        s = compute_review_score(avg_rating=5.0, review_count=100)
        assert s == pytest.approx(1.0)

    def test_no_reviews_returns_neutral(self):
        s = compute_review_score(None, None)
        assert s == pytest.approx(0.5)

    def test_volume_saturates_at_100(self):
        s_100 = compute_review_score(4.0, 100)
        s_500 = compute_review_score(4.0, 500)
        assert s_100 == pytest.approx(s_500)

    def test_zero_rating(self):
        s = compute_review_score(avg_rating=0, review_count=50)
        assert s == pytest.approx(0.3 * 0.5)


class TestAdverseScore:
    def test_clean_record(self):
        assert compute_adverse_score(0) == pytest.approx(1.0)

    def test_one_article_reduces_score(self):
        assert compute_adverse_score(1) == pytest.approx(math.exp(-0.5))

    def test_five_articles_nearly_zero(self):
        assert compute_adverse_score(5) < 0.1

    def test_monotonically_decreasing(self):
        scores = [compute_adverse_score(k) for k in range(6)]
        assert scores == sorted(scores, reverse=True)


class TestSocialScore:
    def test_no_accounts_returns_neutral_floor(self):
        s = compute_social_score(accounts_found=0, activity_score=None, follower_count=None)
        assert s == pytest.approx(0.4)

    def test_floor_applies_even_with_low_activity(self):
        s = compute_social_score(accounts_found=1, activity_score=0.0, follower_count=0)
        assert s >= 0.4

    def test_active_popular_account(self):
        s = compute_social_score(accounts_found=1, activity_score=1.0, follower_count=5000)
        assert s == pytest.approx(1.0)


class TestFinalScore:
    def test_all_perfect_signals_give_ten(self):
        result = compute_final_score(1.0, 1.0, 1.0, 1.0)
        assert result["display_score"] == pytest.approx(10.0)

    def test_all_zero_signals_give_zero(self):
        result = compute_final_score(0.0, 0.0, 0.0, 0.0)
        assert result["display_score"] == pytest.approx(0.0)

    def test_verdict_likely_legit(self):
        result = compute_final_score(1.0, 1.0, 1.0, 1.0)
        assert result["verdict"] == "LIKELY_LEGIT"

    def test_verdict_red_flags(self):
        result = compute_final_score(0.0, 0.0, 0.0, 0.0)
        assert result["verdict"] == "RED_FLAGS"

    def test_verdict_uncertain_at_boundary(self):
        # Neutral signals (0.5 each) should land in UNCERTAIN
        result = compute_final_score(0.5, 0.5, 0.5, 0.5)
        assert result["verdict"] == "UNCERTAIN"

    def test_components_present(self):
        result = compute_final_score(0.8, 0.7, 0.9, 0.6)
        assert "website" in result["components"]
        assert "adverse" in result["components"]

    def test_confidence_score_is_display_times_ten(self):
        result = compute_final_score(0.8, 0.8, 0.8, 0.8)
        assert result["confidence_score"] == pytest.approx(result["display_score"] * 10, rel=0.01)
