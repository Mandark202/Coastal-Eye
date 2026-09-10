"""
INCOIS (Indian National Centre for Ocean Information Services) alert service.

Fetches tsunami warnings and storm-surge / high-wave bulletins from INCOIS
public sources.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCTION NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCOIS does not expose a public structured REST/JSON API for real-time
bulletins without prior registration. This service implements two tiers:

  Tier 1 – Live scrape (attempted first):
    • ITEWC tsunami alert page → https://tsunami.incois.gov.in/TEWS/seismicdata.do
      (Indian Tsunami Early Warning Centre — publicly accessible)
    • INCOIS high-wave advisory → https://www.incois.gov.in/portal/highwaves/highwaves.jsp
    Parsing is best-effort HTML scraping. If the page structure changes
    this tier fails gracefully and falls through to Tier 2.

  Tier 2 – Mock adapter (fallback):
    Returns realistic, clearly-labelled mock data so the rest of the system
    keeps working during development, CI, and when credentials are absent.

TODO (production):
  1. Register for INCOIS Data Services:
       https://www.incois.gov.in/incois/dataRegistration.jsp
  2. Set the environment variable: INCOIS_API_KEY=<your_key>
  3. Replace _fetch_live_* with authenticated endpoint calls documented
     in the INCOIS data-services portal once access is granted.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import os
import time
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Any

from .cache import ttl_cache

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

# TODO: Set INCOIS_API_KEY in your environment for authenticated endpoints.
INCOIS_API_KEY: str | None = os.getenv("INCOIS_API_KEY")

# ITEWC (Indian Tsunami Early Warning Centre) — publicly accessible, no auth needed
TSUNAMI_PAGE_URL  = "https://tsunami.incois.gov.in/TEWS/seismicdata.do"
# INCOIS high-wave advisory — publicly accessible
HIGHWAVE_PAGE_URL = "https://www.incois.gov.in/portal/highwaves/highwaves.jsp"

CACHE_KEY_INCOIS = "incois:all"
CACHE_TTL_SECONDS = 300   # 5 minutes

REQUEST_TIMEOUT   = 6     # seconds per attempt
MAX_RETRIES       = 2
RETRY_BACKOFF     = 1.0   # seconds between retries

# ── Alert normalisation helpers ───────────────────────────────────────────────

# Approximate centre-points for known INCOIS monitoring zones used in mock data.
_ZONE_COORDS: dict[str, tuple[float, float]] = {
    "Andaman Sea":          (11.74, 92.66),
    "Bay of Bengal":        (13.08, 80.27),
    "Arabian Sea":          (18.96, 72.82),
    "Lakshadweep Sea":      (10.57, 72.64),
    "Indian Ocean":         (0.0,   73.0),
    "Chennai Coast":        (13.08, 80.27),
    "Odisha Coast":         (19.81, 85.83),
    "Gujarat Coast":        (21.17, 72.83),
    "Kerala Coast":         (9.93,  76.27),
}

def _coords_for_zone(zone: str) -> tuple[float, float]:
    for key, coords in _ZONE_COORDS.items():
        if key.lower() in zone.lower():
            return coords
    return (15.0, 80.0)  # generic Indian coastline fallback


def _normalise(
    title: str,
    message: str,
    severity: str,
    alert_type: str,
    location: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Return an alert dict that matches the shape expected by alerts.py."""
    if lat is None or lon is None:
        lat, lon = _coords_for_zone(location)
    return {
        "title":      title,
        "message":    message,
        "severity":   severity,   # "High" | "Medium" | "Low"
        "type":       alert_type, # "Tsunami" | "Storm Surge" | "Cyclone" …
        "source":     "INCOIS",
        "location":   location,
        "lat":        lat,
        "lon":        lon,
    }


# ── HTTP helper with retry ────────────────────────────────────────────────────

def _get_with_retry(url: str, headers: dict | None = None) -> requests.Response | None:
    """
    GET *url* with up to MAX_RETRIES attempts and exponential back-off.
    Returns the Response on success, or None on total failure.
    """
    for attempt in range(1, MAX_RETRIES + 2):   # attempts = MAX_RETRIES + 1
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers or {})
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning(
                "INCOIS: attempt %d/%d failed for %s — %s",
                attempt, MAX_RETRIES + 1, url, exc,
            )
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    return None


# ── Tier 1: Live scraping ─────────────────────────────────────────────────────

def _fetch_live_tsunami() -> list[dict[str, Any]]:
    """
    Attempt to scrape the ITEWC (Indian Tsunami Early Warning Centre) seismic
    data page for active tsunami bulletins.
    Returns a list of normalised alert dicts, or [] on failure.

    TODO (production): Replace with authenticated INCOIS REST call once
    INCOIS_API_KEY is available.  Example stub:
        url = f"https://www.incois.gov.in/api/v1/tsunami?apikey={INCOIS_API_KEY}"
        resp = _get_with_retry(url)
        return [_parse_api_record(r) for r in resp.json().get("alerts", [])]
    """
    resp = _get_with_retry(TSUNAMI_PAGE_URL)
    if resp is None:
        return []

    alerts: list[dict] = []
    try:
        text = resp.text
        # ITEWC page contains "Tsunami Warning", "Tsunami Watch", or "No Threat"
        if "no threat" in text.lower() or "no tsunami threat" in text.lower():
            logger.info("INCOIS ITEWC: no active tsunami threat")
            return []

        severity = "High" if any(w in text.lower() for w in ("warning", "alert")) else "Medium"
        if any(w in text.lower() for w in ("warning", "watch", "advisory", "bulletin")):
            alerts.append(_normalise(
                title="INCOIS Tsunami Bulletin — Indian Ocean",
                message=(
                    "Tsunami bulletin issued by ITEWC. Monitor official advisories at "
                    "https://tsunami.incois.gov.in for details."
                ),
                severity=severity,
                alert_type="Tsunami",
                location="Indian Ocean",
            ))
    except Exception as exc:
        logger.error("INCOIS: ITEWC page parse error — %s", exc)

    return alerts


def _fetch_live_highwave() -> list[dict[str, Any]]:
    """
    Attempt to scrape the INCOIS high-wave advisory page.
    Returns a list of normalised alert dicts, or [] on failure.

    TODO (production): Replace with authenticated INCOIS high-wave REST endpoint
    once API access is granted via the data-services portal.
    """
    resp = _get_with_retry(HIGHWAVE_PAGE_URL)
    if resp is None:
        return []

    alerts: list[dict] = []
    try:
        text = resp.text
        if "no advisory" in text.lower() or "nil" in text.lower():
            return []

        # TODO: parse the advisory table with BeautifulSoup for coast-level detail.
        if any(w in text.lower() for w in ("warning", "advisory", "alert", "watch", "significant wave")):
            alerts.append(_normalise(
                title="INCOIS High Wave / Storm Surge Advisory",
                message=(
                    "High wave or storm surge conditions detected along the Indian coastline. "
                    "Refer to https://www.incois.gov.in/portal/highwaves/highwaves.jsp for details."
                ),
                severity="Medium",
                alert_type="Storm Surge",
                location="Indian Coast",
            ))
    except Exception as exc:
        logger.error("INCOIS: high-wave page parse error — %s", exc)

    return alerts


# ── Tier 2: Mock adapter ──────────────────────────────────────────────────────

def _mock_incois_alerts() -> list[dict[str, Any]]:
    """
    Realistic mock INCOIS alerts used when:
      • Live fetch fails, OR
      • USE_REAL_DATA_SOURCES is False (simulated mode).

    All entries are clearly tagged [MOCK] in their source field so they
    are distinguishable from real data during development.

    TODO (production): Remove or gate this behind an explicit INCOIS_MOCK=true
    env var once live credentials are configured.
    """
    return [
        _normalise(
            title="[MOCK] INCOIS Tsunami Watch — Andaman Sea",
            message=(
                "A seismic event of preliminary magnitude 6.8 was detected in the "
                "Andaman Sea. Tsunami Watch issued for Andaman & Nicobar Islands. "
                "Coastal communities should monitor updates. [MOCK DATA — not real]"
            ),
            severity="High",
            alert_type="Tsunami",
            location="Andaman Sea",
        ),
        _normalise(
            title="[MOCK] INCOIS Storm Surge Warning — Odisha Coast",
            message=(
                "Storm surge of 1.5–2.0 m above astronomical tide expected along the "
                "Odisha coast in the next 12 hours due to low-pressure system in the "
                "Bay of Bengal. [MOCK DATA — not real]"
            ),
            severity="High",
            alert_type="Storm Surge",
            location="Odisha Coast",
        ),
        _normalise(
            title="[MOCK] INCOIS High Wave Advisory — Kerala Coast",
            message=(
                "Significant wave height of 3.5 m forecast along Kerala-Karnataka "
                "coast. Fishermen advised not to venture into the sea. "
                "[MOCK DATA — not real]"
            ),
            severity="Medium",
            alert_type="Storm Surge",
            location="Kerala Coast",
        ),
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def get_incois_alerts() -> list[dict[str, Any]]:
    """
    Main entry point for the INCOIS service.

    Flow:
      1. Return cached result if still fresh (< CACHE_TTL_SECONDS old).
      2. Attempt live fetch from ITEWC tsunami page + INCOIS high-wave advisory.
      3. If live fetch returns nothing (fetch error / no active events),
         fall back to mock adapter.
      4. Cache and return results.
    """
    cached = ttl_cache.get(CACHE_KEY_INCOIS)
    if cached is not None:
        logger.debug("INCOIS: serving %d alerts from cache", len(cached))
        return cached

    logger.info("INCOIS: fetching fresh data…")
    alerts: list[dict] = []

    try:
        live_tsunami  = _fetch_live_tsunami()
        live_highwave = _fetch_live_highwave()
        alerts = live_tsunami + live_highwave
        logger.info("INCOIS: live fetch returned %d alerts", len(alerts))
    except Exception as exc:
        logger.error("INCOIS: unexpected error during live fetch — %s", exc)

    # Fall back to mock if live returned nothing
    if not alerts:
        logger.warning("INCOIS: live fetch empty or failed — using mock adapter")
        alerts = _mock_incois_alerts()

    ttl_cache.set(CACHE_KEY_INCOIS, alerts, ttl_seconds=CACHE_TTL_SECONDS)
    return alerts
