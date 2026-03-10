"""
Business Credibility Scoring Model
Weighted linear combination of 4 independent signals.

Each signal returns a normalized score in [0, 1]:
  1.0 = strong legitimacy signal
  0.0 = strong risk signal
  0.4–0.6 = neutral / missing information

Final score:
  Score = 0.30 × S_website + 0.30 × S_reviews + 0.30 × S_adverse + 0.10 × S_social
  CredibilityScore (display) = 10 × Score  →  range [0, 10]

If publicly listed, a 15% multiplier is applied (capped at 10).
Public listing requires SEC/equivalent audited filings — strongest legitimacy signal.

Weights are equal at the top three signals (website, reviews, adverse media)
because each covers a distinct and equally critical dimension of legitimacy.
Social presence acts as a secondary tiebreaker signal.

References:
  - Ma et al. (2009) — domain age + infrastructure as legitimacy features
  - Luca (2016, HBS WP 12-016) — review volume/rating as business legitimacy proxy
  - FATF AML Guidelines (2023) — adverse media as mandatory CDD component
"""
from __future__ import annotations
import math

# weights
W_WEBSITE = 0.30
W_REVIEWS = 0.30
W_ADVERSE = 0.30
W_SOCIAL  = 0.10

assert abs(W_WEBSITE + W_REVIEWS + W_ADVERSE + W_SOCIAL - 1.0) < 1e-9, \
    "Weights must sum to 1"

# verdict thresholds
THRESHOLD_LEGIT     = 7.5   # ≥ 7.5  → LIKELY_LEGIT
THRESHOLD_UNCERTAIN = 5.0   # 5.0–7.5 → UNCERTAIN
                            # < 5.0  → RED_FLAGS


# signal scorers

def compute_website_score(
    domain_age_years: float | None,
    https_enabled: bool | None,
    contact_info_present: bool | None,
    page_quality_count: int = 0,
) -> float:
    """
    S_website = 0.40 × DomainAgeScore + 0.25 × HTTPSScore + 0.20 × ContactScore + 0.15 × PageQualityScore

    DomainAgeScore    = min(age_years / 5, 1)   — caps benefit after 5 years
    HTTPSScore        = 1 if HTTPS, else 0
    ContactScore      = 1 if phone/email/address detected, else 0
    PageQualityScore  = min(page_quality_count / 3, 1)
                        counts: privacy policy, terms of service, about page

    Returns 0.5 (neutral) if all inputs are unknown.
    """
    if domain_age_years is None and https_enabled is None and contact_info_present is None:
        return 0.5  # no data → neutral

    domain_age_score   = min((domain_age_years or 0) / 5.0, 1.0)
    https_score        = 1.0 if https_enabled else 0.0
    contact_score      = 1.0 if contact_info_present else 0.0
    page_quality_score = min(page_quality_count / 3.0, 1.0)

    raw = 0.40 * domain_age_score + 0.25 * https_score + 0.20 * contact_score + 0.15 * page_quality_score
    # New domain (<1 year) is a hard red flag — cap at 0.35 regardless of other signals
    if domain_age_years is not None and domain_age_years < 1:
        raw = min(raw, 0.35)
    return raw


def compute_review_score(
    avg_rating: float | None,
    review_count: int | None,
) -> float:
    """
    S_reviews = 0.4 × RatingScore + 0.6 × VolumeScore

    RatingScore = rating / 5
    VolumeScore = min(review_count / 10000, 1)  — saturates at 10,000 reviews

    Returns 0.5 (neutral) if no review data found.
    """
    if avg_rating is None and review_count is None:
        return 0.5  # no data → neutral

    rating_score = (avg_rating or 0) / 5.0
    volume_score = min((review_count or 0) / 10000.0, 1.0)

    return 0.4 * rating_score + 0.6 * volume_score


def compute_adverse_score(negative_article_count: int) -> float:
    """
    S_adverse = exp(-0.5 × k)

    where k = number of articles mentioning fraud, lawsuits, regulatory action, etc.

    Exponential decay captures asymmetric risk: even a few negative signals
    rapidly reduce credibility.

    k=0 → 1.00   (clean)
    k=1 → 0.61
    k=2 → 0.37
    k=3 → 0.22
    k=5 → 0.08
    """
    return math.exp(-0.5 * negative_article_count)


def compute_social_score(
    accounts_found: int,
    activity_score: float | None,   # 1.0=recent, 0.5=within 1yr, 0.0=dormant
    follower_count: int | None,
) -> float:
    """
    RawScore = 0.4 × AccountExistence + 0.4 × ActivityScore + 0.2 × FollowerScore
    S_social = max(0.4, RawScore)

    The floor of 0.4 ensures absence of social media is treated as neutral,
    not as a risk signal. A 50-year-old B2B manufacturer with no Instagram
    is not suspicious.

    FollowerScore = min(followers / 5000, 1)
    """
    if accounts_found == 0:
        return 0.4  # neutral floor — absence ≠ risk

    account_existence = 1.0
    act_score         = activity_score if activity_score is not None else 0.5
    follower_score    = min((follower_count or 0) / 5000.0, 1.0)

    raw = 0.4 * account_existence + 0.4 * act_score + 0.2 * follower_score
    return max(0.4, raw)



# final aggregator

def compute_final_score(
    s_website: float,
    s_reviews: float,
    s_adverse: float,
    s_social:  float,
    publicly_listed: bool = False,
) -> dict:
    """
    Score = 0.30×S_website + 0.30×S_reviews + 0.30×S_adverse + 0.10×S_social
    CredibilityScore = 10 × Score

    If publicly_listed=True, applies a 15% boost (capped at 1.0).
    Public listing requires SEC/equivalent audited filings — strongest legitimacy signal.

    Returns a dict with the display score, raw score, verdict, and component breakdown.
    """
    raw = (
        W_WEBSITE * s_website +
        W_REVIEWS * s_reviews +
        W_ADVERSE * s_adverse +
        W_SOCIAL  * s_social
    )

    if publicly_listed:
        raw = min(raw * 1.15, 1.0)   # +15% boost, capped at 1.0

    display = round(raw * 10, 1)

    if display >= THRESHOLD_LEGIT:
        verdict = "LIKELY_LEGIT"
    elif display >= THRESHOLD_UNCERTAIN:
        verdict = "UNCERTAIN"
    else:
        verdict = "RED_FLAGS"

    # Convert to 0–100 for the existing confidence_score DB column
    confidence = round(raw * 100, 1)

    return {
        "raw_score":        round(raw, 4),
        "display_score":    display,       # 0–10
        "confidence_score": confidence,    # 0–100 (stored in DB)
        "verdict":          verdict,
        "components": {
            "website": {"score": round(s_website, 3), "weight": W_WEBSITE, "contribution": round(W_WEBSITE * s_website, 4)},
            "reviews": {"score": round(s_reviews, 3), "weight": W_REVIEWS, "contribution": round(W_REVIEWS * s_reviews, 4)},
            "adverse": {"score": round(s_adverse, 3), "weight": W_ADVERSE, "contribution": round(W_ADVERSE * s_adverse, 4)},
            "social":  {"score": round(s_social,  3), "weight": W_SOCIAL,  "contribution": round(W_SOCIAL  * s_social,  4)},
        },
    }