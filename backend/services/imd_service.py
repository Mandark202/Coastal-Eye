"""
IMD (India Meteorological Department) cyclone tracking service.

Fetches active cyclone advisories and track data from IMD public sources.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCTION NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMD does not expose a public structured REST/JSON API for real-time cyclone
data without prior registration. This service implements two tiers:

  Tier 1 – Live sources (attempted in order):
    • WMO Alert Hub CAP feed (aggregates IMD alerts, no auth needed):
        https://api.reliefweb.int/v1/disasters?appname=ctas
      Primary CAP feed:
        https://alert-hub.org/feeds/india
    • IMD current cyclone page → https://www.imd.gov.in/pages/cyclone_current.php
    • IMD RSS / warnings feed  → https://www.imd.gov.in/rss/imd_rss.xml
    Parsing is best-effort HTML/CAP scraping. If the structure changes,
    this tier fails gracefully and falls through to Tier 2.

  Tier 2 – Mock adapter (fallback):
    Returns realistic, clearly-labelled mock data so the rest of the system
    keeps working during development, CI, and when credentials are absent.

TODO (production):
  1. Register at https://mausam.imd.gov.in/ or contact IMD data services.
  2. Set environment variable: IMD_API_KEY=<your_key>
  3. Replace _fetch_live_* functions with authenticated IMD API calls.
     IMD is working toward a National Weather API; check:
     https://www.imd.gov.in/pages/services.php for latest endpoints.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import os
import re
import time
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Any

from .cache import ttl_cache

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

# TODO: Set IMD_API_KEY in your environment when IMD grants API access.
IMD_API_KEY: str | None = os.getenv("IMD_API_KEY")

IMD_CYCLONE_PAGE_URL = "https://www.imd.gov.in/pages/cyclone_current.php"
IMD_RSS_URL          = "https://www.imd.gov.in/rss/imd_rss.xml"
# WMO Alert Hub: aggregates IMD CAP-format alerts, publicly accessible, no auth needed.
# See: https://alert-hub.org  |  Country feed for India:
WMO_CAP_INDIA_URL    = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

CACHE_KEY_IMD    = "imd:cyclones"
CACHE_TTL_SECONDS = 600   # 10 minutes (IMD updates less frequently)

REQUEST_TIMEOUT  = 7      # seconds per attempt
MAX_RETRIES      = 2
RETRY_BACKOFF    = 1.0    # seconds between retries

# ── Region coordinate table ───────────────────────────────────────────────────

_REGION_COORDS: dict[str, tuple[float, float]] = {
    "Bay of Bengal":         (13.08, 80.27),
    "Arabian Sea":           (18.96, 72.82),
    "Andaman":               (11.74, 92.66),
    "Odisha":                (19.81, 85.83),
    "Andhra":                (16.50, 81.72),
    "Tamil Nadu":            (10.79, 79.84),
    "West Bengal":           (21.72, 88.06),
    "Gujarat":               (21.17, 72.83),
    "Kerala":                (9.93,  76.27),
    "Karnataka":             (14.99, 74.12),
    "Mumbai":                (19.08, 72.88),
    "Chennai":               (13.08, 80.27),
    "Cyclone":               (14.00, 80.00),   # generic Bay of Bengal
}

def _coords_for_region(text: str) -> tuple[float, float]:
    for key, coords in _REGION_COORDS.items():
        if key.lower() in text.lower():
            return coords
    return (14.0, 80.0)  # generic Indian east coast fallback


def _normalise(
    title: str,
    message: str,
    severity: str,
    alert_type: str,
    location: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Return an alert dict matching the shape expected by alerts.py."""
    if lat is None or lon is None:
        lat, lon = _coords_for_region(location)
    return {
        "title":    title,
        "message":  message,
        "severity": severity,   # "High" | "Medium" | "Low"
        "type":     alert_type, # "Cyclone" | "Weather" | "Storm"
        "source":   "IMD",
        "location": location,
        "lat":      lat,
        "lon":      lon,
    }


# ── HTTP helper with retry ────────────────────────────────────────────────────

def _get_with_retry(url: str, headers: dict | None = None) -> requests.Response | None:
    """
    GET *url* with up to MAX_RETRIES attempts and linear back-off.
    Returns the Response on success, or None on total failure.
    """
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers or {})
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning(
                "IMD: attempt %d/%d failed for %s — %s",
                attempt, MAX_RETRIES + 1, url, exc,
            )
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    return None


# ── Tier 1: Live scraping ─────────────────────────────────────────────────────

# Patterns to detect cyclone names / positions in raw HTML text.
_CYCLONE_NAME_RE    = re.compile(r"\b(Cyclone|Deep Depression|Depression|BOB|ARB)\s+([A-Z][a-z]+)", re.I)
_INTENSITY_RE       = re.compile(r"(Severe Cyclonic Storm|Cyclonic Storm|Very Severe|Extremely Severe|Super Cyclonic)", re.I)
_LANDFALL_RE        = re.compile(r"landfall.{0,60}(coast|near|over)", re.I)


def _severity_from_intensity(text: str) -> str:
    """Map IMD intensity classification → High / Medium / Low."""
    text_lower = text.lower()
    if any(k in text_lower for k in ("super", "extremely severe", "very severe")):
        return "High"
    if any(k in text_lower for k in ("severe cyclonic", "cyclonic storm")):
        return "High"
    if "deep depression" in text_lower:
        return "Medium"
    return "Low"


def _fetch_live_cyclone_page() -> list[dict[str, Any]]:
    """
    Scrape the IMD current-cyclone page for active systems.

    TODO (production): Replace with authenticated IMD API endpoint once
    IMD_API_KEY is available. Example stub:
        url = f"https://api.imd.gov.in/v1/cyclone/active?apikey={IMD_API_KEY}"
        resp = _get_with_retry(url)
        return [_parse_imd_record(r) for r in resp.json().get("systems", [])]
    """
    resp = _get_with_retry(IMD_CYCLONE_PAGE_URL)
    if resp is None:
        return []

    alerts: list[dict] = []
    try:
        text = resp.text

        # Quick check — if IMD says no active system, bail early.
        if re.search(r"no (active|current) cyclone", text, re.I):
            logger.info("IMD: cyclone page reports no active systems")
            return []

        # Find any named cyclone / depression
        names     = _CYCLONE_NAME_RE.findall(text)
        intensity = _INTENSITY_RE.search(text)
        landfall  = _LANDFALL_RE.search(text)

        if names or intensity:
            sys_name  = f"Cyclone {names[0][1]}" if names else "Tropical System"
            int_label = intensity.group(0) if intensity else "Depression"
            severity  = _severity_from_intensity(int_label)

            message = (
                f"IMD tracking: {int_label}. "
                + (f"Landfall expected {landfall.group(0)}. " if landfall else "")
                + "Follow IMD advisories. Visit https://www.imd.gov.in for details."
            )
            # Try to infer basin
            basin = "Bay of Bengal" if "BOB" in text.upper() else (
                "Arabian Sea" if "ARB" in text.upper() else "Bay of Bengal"
            )
            alerts.append(_normalise(
                title=f"IMD Advisory: {sys_name}",
                message=message,
                severity=severity,
                alert_type="Cyclone",
                location=basin,
            ))
    except Exception as exc:
        logger.error("IMD: cyclone page parse error — %s", exc)

    return alerts


def _fetch_live_rss() -> list[dict[str, Any]]:
    """
    Parse the IMD RSS feed for weather warnings.
    Supplements the cyclone page with general severe-weather items.

    TODO (production): If IMD provides a dedicated cyclone RSS, swap the URL here.
    """
    resp = _get_with_retry(IMD_RSS_URL)
    if resp is None:
        return []

    alerts: list[dict] = []
    try:
        root    = ET.fromstring(resp.text)
        channel = root.find("channel")
        items   = channel.findall("item") if channel else root.findall(".//item")

        for item in items[:8]:
            title = (item.findtext("title")       or "").strip()
            desc  = (item.findtext("description") or "").strip()

            # Only surface cyclone / storm / warning items
            combined = (title + " " + desc).lower()
            if not any(k in combined for k in ("cyclone", "storm", "warning", "alert", "watch")):
                continue

            severity = "High" if "warning" in combined else "Medium"
            atype    = "Cyclone" if "cyclone" in combined else "Weather"
            location = "Bay of Bengal"   # IMD RSS items rarely carry coordinates

            alerts.append(_normalise(
                title=title or "IMD Weather Warning",
                message=desc[:300] or "See IMD portal for details.",
                severity=severity,
                alert_type=atype,
                location=location,
            ))

    except ET.ParseError as exc:
        logger.error("IMD: RSS parse error — %s", exc)

    return alerts[:5]


# ── Tier 1c: WMO Alert Hub CAP feed ──────────────────────────────────────────

def _fetch_wmo_cap_alerts() -> list[dict[str, Any]]:
    """
    Fetch IMD CAP (Common Alerting Protocol) alerts from the WMO Alert Hub.

    The WMO Alert Hub (https://alert-hub.org) aggregates machine-readable
    CAP-format XML feeds from IMD and other national met services.
    This feed is publicly accessible without credentials.

    IMD CAP feed aggregated by WMO:
        https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml

    Returns a list of normalised alert dicts, or [] on failure.
    """
    resp = _get_with_retry(WMO_CAP_INDIA_URL)
    if resp is None:
        return []

    alerts: list[dict] = []
    try:
        root    = ET.fromstring(resp.text)
        channel = root.find("channel")
        items   = channel.findall("item") if channel else root.findall(".//item")

        for item in items[:10]:
            title = (item.findtext("title")       or "").strip()
            desc  = (item.findtext("description") or "").strip()
            combined = (title + " " + desc).lower()

            # Only surface storm / cyclone / weather warnings
            if not any(k in combined for k in ("cyclone", "storm", "warning", "alert", "watch", "flood")):
                continue

            severity = "High" if any(k in combined for k in ("warning", "red", "extreme")) else "Medium"
            atype    = "Cyclone" if "cyclone" in combined else ("Flood" if "flood" in combined else "Weather")
            location = "India"

            # Try to infer specific coast from title / description
            for region in ("Bay of Bengal", "Arabian Sea", "Andaman", "Odisha",
                           "Gujarat", "Tamil Nadu", "Andhra", "Kerala",
                           "Karnataka", "Mumbai", "Chennai", "West Bengal"):
                if region.lower() in combined:
                    location = region
                    break

            alerts.append(_normalise(
                title=title or "IMD Advisory (WMO Alert Hub)",
                message=desc[:300] or "IMD advisory issued. See https://alert-hub.org for details.",
                severity=severity,
                alert_type=atype,
                location=location,
            ))

    except ET.ParseError as exc:
        logger.error("IMD WMO CAP: RSS/CAP parse error — %s", exc)
    except Exception as exc:
        logger.error("IMD WMO CAP: unexpected error — %s", exc)

    logger.info("IMD WMO CAP: returned %d alerts", len(alerts))
    return alerts[:5]


# ── Tier 2: Mock adapter ──────────────────────────────────────────────────────

def _mock_imd_alerts() -> list[dict[str, Any]]:
    """
    Realistic mock IMD alerts used when:
      • Live fetch fails, OR
      • USE_REAL_DATA_SOURCES is False (simulated mode).

    All entries are clearly tagged [MOCK] so they are distinguishable from
    real data during development.

    TODO (production): Remove or gate behind IMD_MOCK=true env var once
    live credentials and stable endpoints are available.
    """
    return [
        _normalise(
            title="[MOCK] IMD Cyclone Warning — Bay of Bengal",
            message=(
                "Cyclonic Storm BIPARJOY intensified over the north-central Bay of "
                "Bengal. Landfall expected near Odisha-West Bengal coast within 48 h. "
                "Wind speed 90–100 km/h, gusting to 110 km/h. Fishermen must not "
                "venture into sea. [MOCK DATA — not real]"
            ),
            severity="High",
            alert_type="Cyclone",
            location="Bay of Bengal",
        ),
        _normalise(
            title="[MOCK] IMD Severe Cyclone Warning — Arabian Sea",
            message=(
                "Very Severe Cyclonic Storm TAUKTAE tracking toward Gujarat coast. "
                "Landfall expected in 24 h. Wind speed 160–170 km/h. "
                "Red alert issued for coastal districts. [MOCK DATA — not real]"
            ),
            severity="High",
            alert_type="Cyclone",
            location="Gujarat Coast",
            lat=21.17, lon=72.83,
        ),
        _normalise(
            title="[MOCK] IMD Heavy Rainfall Red Alert — Tamil Nadu",
            message=(
                "Extremely heavy rainfall (≥ 20 cm in 24 h) likely over the Tamil Nadu "
                "coast due to low-pressure area in the Bay of Bengal. "
                "[MOCK DATA — not real]"
            ),
            severity="Medium",
            alert_type="Weather",
            location="Tamil Nadu",
        ),
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def get_imd_alerts() -> list[dict[str, Any]]:
    """
    Main entry point for the IMD service.

    Flow:
      1. Return cached result if still fresh (< CACHE_TTL_SECONDS old).
      2. Attempt live fetch from three independent sources:
           a. WMO Alert Hub CAP feed (public, no auth)  ← most reliable
           b. IMD cyclone current page (HTML scrape)
           c. IMD RSS feed (HTML scrape)
      3. Merge results, de-duplicate by title.
      4. If all live sources return nothing, fall back to mock adapter.
      5. Cache and return results.
    """
    cached = ttl_cache.get(CACHE_KEY_IMD)
    if cached is not None:
        logger.debug("IMD: serving %d alerts from cache", len(cached))
        return cached

    logger.info("IMD: fetching fresh data...")
    raw_alerts: list[dict] = []

    try:
        wmo_alerts  = _fetch_wmo_cap_alerts()    # public, most reliable
        page_alerts = _fetch_live_cyclone_page()  # scrape
        rss_alerts  = _fetch_live_rss()           # scrape
        raw_alerts  = wmo_alerts + page_alerts + rss_alerts
    except Exception as exc:
        logger.error("IMD: unexpected error during live fetch — %s", exc)

    # De-duplicate by title across all sources
    alerts: list[dict] = []
    seen_titles: set[str] = set()
    for a in raw_alerts:
        if a["title"] not in seen_titles:
            alerts.append(a)
            seen_titles.add(a["title"])

    logger.info("IMD: live fetch returned %d unique alerts", len(alerts))

    # Fall back to mock if all live sources returned nothing
    if not alerts:
        logger.warning("IMD: all live sources empty or failed — using mock adapter")
        alerts = _mock_imd_alerts()

    ttl_cache.set(CACHE_KEY_IMD, alerts, ttl_seconds=CACHE_TTL_SECONDS)
    return alerts
