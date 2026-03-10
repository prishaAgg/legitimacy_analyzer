"""
signals/website.py
Domain/website analysis: WHOIS age, SSL, contact info, reachability.
Uses: python-whois, httpx (no API key required)
Scoring: compute_website_score() from services/scoring.py
  S_website = 0.40 × DomainAge + 0.25 × HTTPS + 0.20 × Contact + 0.15 × PageQuality
"""
from __future__ import annotations

import httpx
import ssl
import socket
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.schemas.response import SignalResult
from app.services.signals.base import BaseSignal


# Directories and aggregators that are never the official website
SKIP_DOMAINS = [
    "yelp.com", "facebook.com", "linkedin.com", "bbb.org",
    "yellowpages", "google.com", "wikipedia.org", "reddit.com",
    "twitter.com", "x.com", "instagram.com", "youtube.com",
    "tripadvisor.com", "trustpilot.com", "glassdoor.com",
    "indeed.com", "zoominfo.com", "bloomberg.com", "crunchbase.com",
]


class WebsiteSignal(BaseSignal):
    name = "website"

    async def collect(self, business_name: str, location: str | None) -> SignalResult:
        try:
            return await self._run(business_name, location)
        except Exception as exc:
            return self._error_result(exc)

    async def _run(self, business_name: str, location: str | None) -> SignalResult:
        website_url = await self._find_website(business_name, location)

        if not website_url:
            return SignalResult(
                name=self.name,
                status="not_found",
                score=50,
                summary="Could not identify an official website for this business.",
                sources=[],
            )

        parsed   = urlparse(website_url)
        hostname = parsed.hostname or ""
        details: dict = {"url": website_url}

        https_enabled        = False
        contact_info_present = False
        domain_age_years     = None

        # 1. Reachability + contact scan
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                resp = await client.get(website_url)
                details["reachable"]    = True
                details["status_code"]  = resp.status_code
                text = resp.text.lower()
                details["has_phone"]   = bool(re.search(r'\b\d{3}[-.\\s]?\d{3}[-.\\s]?\d{4}\b', text))
                details["has_email"]   = bool(re.search(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', text))
                details["has_address"] = any(w in text for w in ["address", "street", "ave ", "blvd", "suite"])
                contact_info_present   = any([details["has_phone"], details["has_email"], details["has_address"]])

                # Page quality signals — checks for professional site structure
                details["has_privacy_policy"] = any(w in text for w in ["privacy policy", "privacy-policy", "/privacy"])
                details["has_terms"]          = any(w in text for w in ["terms of service", "terms and conditions", "terms of use", "/terms"])
                details["has_about"]          = any(w in text for w in ["about us", "about-us", "/about", "our story", "who we are"])
                # Professional email: site has a non-free-provider email domain
                email_match = re.search(r'[a-z0-9._%+-]+@([a-z0-9.-]+\.[a-z]{2,})', text)
                free_providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
                details["has_professional_email"] = bool(
                    email_match and email_match.group(1) not in free_providers
                )
        except Exception as e:
            details["reachable"] = False
            details["error"]     = str(e)

        # 2. SSL
        if hostname:
            ssl_info      = self._check_ssl(hostname)
            details["ssl"] = ssl_info
            https_enabled  = ssl_info.get("valid", False)

        # 3. Domain age via WHOIS
        if hostname:
            whois_info       = self._get_whois_age(hostname)
            details["whois"] = whois_info
            age_days         = whois_info.get("age_days") or 0
            domain_age_years = age_days / 365.25

        # Page quality composite
        page_quality_flags = [
            details.get("has_privacy_policy"),
            details.get("has_terms"),
            details.get("has_about"),
            details.get("has_professional_email"),
        ]
        page_quality_count = sum(1 for f in page_quality_flags if f)

        from app.services.scoring import compute_website_score
        s = compute_website_score(domain_age_years, https_enabled, contact_info_present, page_quality_count)

        details["scoring"] = {
            "domain_age_years":       round(domain_age_years, 2) if domain_age_years is not None else None,
            "https_enabled":          https_enabled,
            "contact_info_present":   contact_info_present,
            "page_quality_count":     page_quality_count,
            "normalized_score":       round(s, 3),
        }

        parts = []
        parts.append(f"Website reachable ({details.get('status_code')})" if details.get("reachable") else "Website unreachable")
        parts.append("SSL valid" if https_enabled else "SSL missing or invalid")
        if domain_age_years:
            yrs = int(domain_age_years)
            mos = int((domain_age_years % 1) * 12)
            parts.append(f"Domain {yrs}y {mos}m old")
        parts.append("Contact info found" if contact_info_present else "No contact info detected")
        if page_quality_count >= 3:
            parts.append("Privacy policy, terms, and About page detected")
        elif page_quality_count >= 1:
            quality_items = []
            if details.get("has_privacy_policy"): quality_items.append("privacy policy")
            if details.get("has_terms"):          quality_items.append("terms")
            if details.get("has_about"):          quality_items.append("about page")
            parts.append(f"Found: {', '.join(quality_items)}")

        return SignalResult(
            name=self.name,
            status="found",
            score=round(s * 100),
            summary=". ".join(parts) + ".",
            details=details,
            sources=[website_url],
        )

    # private helpers

    async def _find_website(self, business_name: str, location: str | None) -> str | None:
        from app.services.signals.google_client import search_google

        query = f"{business_name} official website"
        if location:
            query += f" {location}"

        items = await search_google(query, num=5)
        if not items:
            return None

        # Pass 1: prefer root domains not in skip list
        for item in items:
            url    = item.get("link", "")
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            path   = parsed.path.rstrip("/")

            if any(s in domain for s in SKIP_DOMAINS):
                continue

            # Prefer root or shallow paths (home page)
            if path in ("", "/") or path.count("/") <= 1:
                return url

        # Pass 2: any non-skip result
        for item in items:
            url    = item.get("link", "")
            domain = urlparse(url).netloc.lower()
            if not any(s in domain for s in SKIP_DOMAINS):
                return url

        # Last resort: first result even if in skip list
        return items[0].get("link") if items else None

    def _check_ssl(self, hostname: str) -> dict:
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.settimeout(5)
                s.connect((hostname, 443))
                cert      = s.getpeercert()
                expire_str = cert.get("notAfter", "")
                expire_dt  = datetime.strptime(expire_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left  = (expire_dt - datetime.now(timezone.utc)).days
                return {"valid": True, "expires_in_days": days_left, "expires": expire_str}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _get_whois_age(self, domain: str) -> dict:
        try:
            import whois
            w        = whois.whois(domain)
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]
            if creation:
                if creation.tzinfo is None:
                    creation = creation.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - creation).days
                return {"created": str(creation.date()), "age_days": age_days}
            return {"created": None, "age_days": None}
        except Exception as e:
            return {"error": str(e)}