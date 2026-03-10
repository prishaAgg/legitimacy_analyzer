# Socratix — Business Legitimacy Analyzer

A full-stack business intelligence tool that aggregates signals from across the web to assess whether a business is legitimate. Enter a business name and optional location, and the app returns a credibility score (0–10), a verdict, and a structured breakdown of evidence across five independent signal categories.

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- API keys (see below)

### API Keys

| Key | Where to get it | Required? |
|-----|----------------|-----------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Recommended — enables AI synthesis and cross-signal validation |
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) — 2,500 free searches, no credit card | Recommended — powers website, reviews, and social signals |
| `NEWS_API_KEY` | [newsapi.org](https://newsapi.org) — 100 req/day free | Recommended — adverse media screening |
| `GUARDIAN_API_KEY` | [open-platform.theguardian.com](https://open-platform.theguardian.com) — 500 req/day free | Recommended — recent news coverage |

No key is needed for the stock listing signal (Yahoo Finance, direct HTTP). (Although the yf blocks this.)

### Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd socratix

# 2. Create your .env file
cp backend/.env.example backend/.env
# Fill in your API keys in backend/.env

# 3. Build and run
docker-compose up --build
```

The app will be available at **http://localhost:8080**.  
The API runs at **http://localhost:8000**.  

---

## Signals: What We Check and Why

Five independent signals were chosen to cover distinct, non-overlapping dimensions of business legitimacy. Each is grounded in established research or industry practice.

### 1. Website Credibility
Checks the official website for domain age, HTTPS, contact information, and page quality indicators (privacy policy, terms of service, about page).

**Why:** Domain age and infrastructure are among the most reliable legitimacy signals available without human judgment. Ma et al. (2009) demonstrate that domain age and SSL are strong predictors of legitimacy. Scam sites typically have brand-new domains and lack legal pages. A domain under one year old is treated as a hard red flag regardless of other signals.

**Formula:**
```
S_website = 0.40 × DomainAge + 0.25 × HTTPS + 0.20 × ContactInfo + 0.15 × PageQuality
```
where DomainAge saturates at 5 years, PageQuality counts privacy policy + terms + about page.

### 2. Customer Reviews
Aggregates review data from Yelp, Trustpilot, and Google Maps via Serper.

**Why:** Luca (HBS Working Paper 12-016, 2016) establishes review volume as a proxy for business legitimacy — the sheer existence of thousands of reviews confirms a business is real and operational. Crucially, **volume is weighted more heavily than rating** (0.6 vs 0.4) because large legitimate businesses (banks, airlines, Apple) often have low average ratings due to selection bias — unhappy customers review more than happy ones.

**Formula:**
```
S_reviews = 0.4 × (avg_rating / 5) + 0.6 × min(review_count / 10000, 1)
```

### 3. Adverse Media
Screens for negative press coverage using two complementary sources run in parallel: The Guardian API for recent coverage context, and NewsAPI for adverse keyword screening (fraud, lawsuit, scam, regulatory action, etc.).

**Why:** Adverse media screening is a mandatory component of Customer Due Diligence (CDD) under FATF AML Guidelines (2023). The exponential decay formula captures the asymmetric nature of risk — even a small number of adverse articles should significantly reduce credibility.

**Formula:**
```
S_adverse = exp(-0.5 × k)   where k = number of adverse articles
k=0 → 1.00  |  k=1 → 0.61  |  k=2 → 0.37  |  k=5 → 0.08
```

### 4. Social Presence
Checks for active accounts on LinkedIn, Facebook, Instagram, Twitter/X, and YouTube via Serper.

**Why:** An established business almost always has at least one active social profile. Absence is treated as neutral (not a risk signal) — a 50-year-old B2B manufacturer with no Instagram is not suspicious. The floor of 0.4 ensures this signal never penalizes a business for lacking social media.

### 5. Stock Listing
Checks Yahoo Finance's search API for a public listing. Uses fuzzy string matching (60% threshold) to avoid false positives.

**Why:** A publicly traded company must file audited financial statements with the SEC or equivalent regulator — the strongest possible legitimacy signal. This signal acts as a score multiplier (+15%, capped at 10) rather than a weighted component, since not being listed carries no negative implication.

---

## Scoring Model

```
Score = 0.30 × S_website + 0.30 × S_reviews + 0.30 × S_adverse + 0.10 × S_social
CredibilityScore (display) = Score × 10    →    range: 0–10

If publicly_listed = True:  Score = min(Score × 1.15, 1.0)
```

The three primary signals (website, reviews, adverse media) are weighted equally because each covers an equally critical and independent dimension of legitimacy. Social presence is a secondary tiebreaker at 10%.

**Verdict thresholds:**
| Score | Verdict |
|-------|---------|
| ≥ 7.5 | Likely Legitimate |
| 5.0 – 7.5 | Uncertain |
| < 5.0 | Red Flags |

### Scoring Without API Keys

The app degrades gracefully when API keys are missing:

- **No Serper key:** Website, reviews, and social signals return a neutral score of 0.5. The score is computed from whatever signals are available.
- **No Guardian / NewsAPI keys:** Adverse media returns neutral (0.5). No adverse penalty is applied — absence of data is not treated as clean.
- **No Anthropic key:** The fallback synthesizer runs the weighted formula directly and generates a structured verdict from the raw scores. All signal cards are still populated with raw findings. The only loss is the AI layer that validates cross-signal coherence and catches ambiguous business names.

This means the tool is functional with zero API keys — it just provides less precise results.

---

## AI Synthesis (Anthropic)

When an Anthropic API key is configured, all signal results are passed to Claude, which:

- Validates that signals are coherent with each other (e.g., flags if the website found doesn't match the searched company)
- Catches name ambiguity (e.g., "Apple" could be Apple Inc. or Apple Records)
- Adjusts score weighting based on business type (e.g., domain age matters less for a recently-launched tech startup, more for a financial institution)
- Produces a human-readable reasoning summary
- Flags potential misspellings or disambiguation issues via `nameFlag`

Without the Anthropic key, each signal is evaluated independently. Cross-signal validation does not occur — this is the most significant capability gap between keyed and keyless operation.

---

## Data Storage

The app uses **SQLite** with **SQLAlchemy** (async via `aiosqlite`). All analysis runs are persisted so users can review past reports.

### Schema

```
search_runs
├── id              TEXT PRIMARY KEY   (UUID)
├── business_name   TEXT
├── location        TEXT
├── status          TEXT               (pending / running / complete / error)
├── result_json     TEXT               (full DossierReport as JSON)
├── confidence_score REAL              (0–100, mirrors display score × 10)
├── verdict         TEXT
├── created_at      DATETIME
└── completed_at    DATETIME
```

### Design Decisions

**SQLite over PostgreSQL:** SQLite requires zero infrastructure — no separate database container, no connection string management. For a single-user analyst tool, SQLite handles concurrent reads well and persists via a named Docker volume (`sqlite_data`). The volume survives container restarts.

**Full JSON storage:** The entire `result_json` is stored rather than normalizing signals into separate tables. This preserves the full signal output including sources, scoring breakdowns, and metadata without requiring schema migrations when signal structure changes.

**Timeline over deduplication:** Repeated searches for the same business create new rows. This is intentional — an analyst tool benefits from historical comparison. Running "Acme Corp" in January and again in June should produce two separate records that can be compared.

---

## Adding a New Signal

The signal architecture is designed for easy extension. To add a signal:

**Step 1: Create the signal file**

```python
# backend/app/services/signals/my_signal.py
from app.services.signals.base import BaseSignal
from app.schemas.response import SignalResult

class MySignal(BaseSignal):
    name = "my_signal"

    async def collect(
        self,
        business_name: str,
        location: str | None,
        canonical_domain: str | None = None,
    ) -> SignalResult:
        # Your logic here
        return SignalResult(
            name=self.name,
            status="found",       # found | not_found | error
            score=75,             # 0–100, or None if used as multiplier
            summary="One-line summary shown in the UI",
            sources=["https://source.com"],
            details={"key": "value"},  # arbitrary metadata
        )
```

**Step 2: Register it in the orchestrator**

```python
# backend/app/services/orchestrator.py
from app.services.signals.my_signal import MySignal

PHASE_2_SIGNALS: list[type] = [
    ReviewsSignal,
    AdverseMediaSignal,
    SocialSignal,
    StockSignal,
    MySignal,   # ← add here
]
```

**Step 3: Add a formatter**

```python
# backend/app/services/formatter.py
def _fmt_my_signal(signal: dict) -> dict:
    findings = []
    # extract from signal["details"] and build findings list
    return {
        "title":          "My Signal",
        "findings":       findings,
        "interpretation": "...",
        "source":         "Source description",
        "sources":        signal.get("sources", []),
    }
```

Add `"my_signal": _fmt_my_signal` to the `FORMATTERS` dict in the same file.

That's it. No other files need to change.

---

## Architecture

```
┌─────────────────────────────────┐
│   React Frontend (Vite + TS)    │  localhost:8080
│   Tailwind CSS + shadcn/ui      │
└────────────┬────────────────────┘
             │ REST (polling)
┌────────────▼────────────────────┐
│   FastAPI Backend               │  localhost:8000
│   Async Python 3.9              │
│                                 │
│  POST /api/runs/                │  ← submit job
│  GET  /api/runs/{id}            │  ← poll status
│  GET  /api/analyze-business/{id}│  ← fetch report
│  GET  /api/analyze-business/    │
│       history                   │  ← past runs
└──────┬──────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  Orchestrator                                        │
│  Phase 1: WebsiteSignal (discovers canonical domain) │
│  Phase 2: Reviews + AdverseMedia + Social + Stock    │
│           (run concurrently via asyncio.gather)      │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  Synthesizer → Claude (or fallback scoring)          │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────┐
│  SQLite + ORM   │  (persisted via Docker volume)
└─────────────────┘
```

**Why FastAPI:** Async-first, which is critical since signal collection involves 5+ concurrent HTTP calls to external APIs. A synchronous framework (Flask/Django) would serialize these calls and 5× the response time.

**Why async job pattern (POST → poll):** Signal collection takes 5–15 seconds. A synchronous request would time out in many browsers and proxies. The job pattern lets the frontend show a loading state and poll independently.

---

## Limitations

These are known constraints that are optimal for the current scale and solvable with additional resources:

**API dependencies:** Signal quality is bounded by what free-tier APIs return. Serper's search snippets are brief, which limits rating/review extraction accuracy. With a paid Yelp Fusion API or Google Places API, review data would be significantly more reliable.

**Business name ambiguity:** Searching "Apple" without a location may return results for Apple Inc., Apple Records, or a local business. The Anthropic synthesis layer partially addresses this by cross-validating signals — but without the AI key, signals are evaluated independently. A future improvement would use the discovered website domain to anchor downstream queries.

**Citation relevance:** Articles and links shown in signal cards are not guaranteed to be about the searched business. The Guardian API and NewsAPI match on business name string, so "Apple" may surface articles about Apple Inc., Apple Records, or unrelated uses of the word — even with the headline-match filter applied. Review links from Serper carry the same risk. The Anthropic synthesis layer partially mitigates this by cross-validating signals for coherence, but without the AI key no such validation occurs. The full solution is cross-signal anchoring: using the canonical domain from the website signal (e.g. apple.com) to anchor all downstream queries. The two-phase orchestrator is already structured for this; it was not implemented due to API query format constraints with Serper.

**Consistency:** Results can vary between runs due to search engine result fluctuation and Guardian/NewsAPI index freshness. `temperature=0` is set on the Claude API call to minimize score variance from the AI layer, but signal data itself is non-deterministic.

**Stock listing signal:** The Yahoo Finance search endpoint is unofficial and blocks requests from cloud/container IP ranges. The signal architecture and fuzzy matching logic are complete; for production deployment this would be replaced with a Financial Modeling Prep or Polygon.io API.

**SQLite concurrency:** SQLite handles concurrent reads well but has write locking. For multi-user deployment, this would be a bottleneck.

---

## Future Directions

### Better Data Sources
- Replace Serper with **Yelp Fusion API** or **Google Places API** for structured review data (rating, count, recency) rather than regex-parsed snippets
- Replace Yahoo Finance with **Financial Modeling Prep** or **Polygon.io** for reliable stock listing data with an SLA
- Add **Companies House API** (UK) or **OpenCorporates** for official business registration verification
- Add **SEC EDGAR API** for US public company filings

### Additional Signals
- **Business registration:** State/federal incorporation databases — currently fragmented across 50 states with no unified API, but OpenCorporates provides partial coverage
- **Website quality scoring:** Broken link detection, grammar analysis, stock photo density — all feasible from the HTML already fetched
- **LinkedIn employee count:** Proxy for company size; partially extractable from Serper snippets today
- **Domain reputation:** Services like Cisco Talos or URLVoid score domains against threat databases

### Scaling the Architecture
- **PostgreSQL:** Replace SQLite to support multiple concurrent users, user accounts, saved watchlists, and team-shared reports. Schema migration is straightforward — SQLAlchemy abstracts the dialect.
- **Redis + Celery:** Replace the in-memory async job pattern with a proper task queue for horizontal scaling and job persistence across restarts
- **Anthropic at scale:** Claude works well for synthesis but costs approximately $0.003–0.015 per analysis at current pricing. At high volume, a lighter model (Haiku) for initial triage and Sonnet only for uncertain cases would reduce costs significantly. Caching synthesis results for identical business+location queries would also help.
- **Signal result caching:** Cache signal results for a business by domain for 24 hours. Many repeat lookups would hit cache and return instantly.
- **Cross-signal anchoring:** Once the website signal identifies the canonical domain, pass it to reviews and adverse media as a search anchor to prevent cross-company contamination. The orchestrator already runs website first (Phase 1) in preparation for this.

---

## Trade-offs Made

| Decision | What I chose | What I'd do with more time |
|----------|-------------|---------------------------|
| **Database** | SQLite — zero infrastructure, works out of the box | PostgreSQL for multi-user support and better concurrency |
| **Review data** | Regex-parse Serper snippets | Yelp Fusion or Google Places for structured rating + count data |
| **Stock listing** | Yahoo Finance direct HTTP — no API key needed | Financial Modeling Prep or Polygon.io for a supported endpoint |
| **Job queue** | In-memory async (asyncio) | Redis + Celery for persistence across restarts and horizontal scaling |
| **AI synthesis** | Claude Sonnet with `temperature=0` for determinism | Fine-tuned triage model (Haiku) for cheap initial pass, Sonnet only for uncertain cases |
| **Cross-signal validation** | Business name string matching per signal | Use discovered website domain as anchor for downstream queries once website signal resolves |
| **Signal coverage** | 5 signals via free/unofficial APIs | Add Companies House, SEC EDGAR, Yelp Fusion, LinkedIn official API |
| **Frontend state** | React polling every 2s | WebSocket push for real-time status without polling overhead |

---

## What I'm Particularly Proud Of

**The scoring model is defensible, not arbitrary.** Every weight and formula has a rationale tied to published research (Ma et al. 2009 on domain age, Luca 2016 on review volume, FATF AML guidelines on adverse media). The decision to weight review volume more heavily than rating — because legitimacy ≠ quality — is a genuine product insight, not a default choice.

**Graceful degradation is a first-class feature.** The app works with zero API keys. Each signal fails independently and returns a neutral score rather than crashing the analysis. A user with not using the Anthropic key gets a reasonable result; a user with all keys gets a significantly better one. This was a deliberate design decision, not an afterthought.

**The two-phase orchestrator.** Website runs first to discover the canonical domain, then all other signals run concurrently. This sets up proper cross-signal anchoring as a natural next step — the architecture already supports it, it just needs the downstream query changes.

**The adverse media signal uses two complementary sources by design.** Guardian API provides recent coverage context (informational); NewsAPI screens for adverse keywords (risk signal). They serve different purposes and run in parallel. Separating them means a business with lots of Guardian coverage but no adverse keywords correctly scores as neutral-to-positive on this dimension.

**The new-domain hard cap.** A domain under one year old caps the website score at 35/100 regardless of HTTPS or contact info. This is a deliberate asymmetric rule — the cost of missing a legitimate new business is low, while the cost of green-lighting a scam site is high. The scoring model encodes that judgment explicitly.