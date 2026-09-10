"""
Alerts router for the Coastal Threat Alert System (CTAS).

Alert pipeline (in priority order):
  1. LIVE geo-aware data  — Open-Meteo weather + USGS earthquakes (existing)
  2. REAL Indian sources  — INCOIS (tsunami/surge) + IMD (cyclone) [NEW]
     Only active when  USE_REAL_DATA_SOURCES=true  env var is set.
  3. DB alerts            — community-reported / persisted alerts (existing)

All three tiers are independent; a failure in any one is logged and skipped
so the others always run.
"""

from __future__ import annotations

import os
import logging
import datetime
import random
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert
from ..services.alert_ranking import rank_alerts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Alerts"])

# ── Feature flag ──────────────────────────────────────────────────────────────
# Set  USE_REAL_DATA_SOURCES=true  in your environment to activate INCOIS + IMD.
# When false (the default), the system runs in fully-simulated mode as before.
USE_REAL_DATA_SOURCES: bool = (
    os.getenv("USE_REAL_DATA_SOURCES", "false").strip().lower() == "true"
)

if USE_REAL_DATA_SOURCES:
    logger.info("CTAS Alerts: USE_REAL_DATA_SOURCES=true — INCOIS + IMD enabled")
else:
    logger.info("CTAS Alerts: USE_REAL_DATA_SOURCES=false — simulated mode only")

# IST timezone constant (reused below)
_IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


# ── Helper: convert raw alert dict → response dict ────────────────────────────

def _raw_to_response(
    raw: dict[str, Any],
    lat_hint: float | None = None,
    lon_hint: float | None = None,
) -> dict[str, Any]:
    """
    Normalise a raw alert dict (from any service) into the response schema
    that the frontend already understands.
    """
    severity = raw.get("severity", "Low")
    return {
        "id":             random.randint(10_000, 99_999),  # ephemeral ID for frontend
        "location":       raw.get("location", "Nearby Region"),
        "lat":            raw.get("lat", lat_hint or 0.0),
        "lon":            raw.get("lon", lon_hint or 0.0),
        "title":          raw.get("title", "Alert"),
        "message":        raw.get("message", ""),
        "severity":       severity,
        "alert_type":     raw.get("type", "Unknown"),
        "source":         raw.get("source", "Unknown"),
        "created_at":     datetime.datetime.now(_IST),
        "distance_km":    0,
        "cpi":            50,
        "priority_score": 100 if severity == "High" else (50 if severity == "Medium" else 10),
    }


# ── Helper: fetch real Indian-source alerts ───────────────────────────────────

def _get_real_indian_alerts() -> list[dict[str, Any]]:
    """
    Fetch alerts from INCOIS and IMD services.

    Each service is called independently so a failure in one does not
    prevent the other from contributing alerts.
    Returns an empty list on total failure — simulated path still runs.
    """
    results: list[dict] = []

    # ── INCOIS (tsunami + storm surge) ────────────────────────────────────────
    try:
        from ..services.incois_service import get_incois_alerts
        incois_alerts = get_incois_alerts()
        results.extend(incois_alerts)
        logger.info("Alerts: INCOIS returned %d alerts", len(incois_alerts))
    except Exception as exc:
        logger.error("Alerts: INCOIS fetch failed — %s", exc)

    # ── IMD (cyclone tracking) ────────────────────────────────────────────────
    try:
        from ..services.imd_service import get_imd_alerts
        imd_alerts = get_imd_alerts()
        results.extend(imd_alerts)
        logger.info("Alerts: IMD returned %d alerts", len(imd_alerts))
    except Exception as exc:
        logger.error("Alerts: IMD fetch failed — %s", exc)

    return results


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.get("/alerts")
def get_alerts(
    lat: float = None,
    lon: float = None,
    radius_km: float = 50,
    db: Session = Depends(get_db),
):
    """
    Get active coastal alerts.

    Query params:
      lat / lon   — user coordinates (enables geo-aware live fetch + ranking)
      radius_km   — proximity filter radius (used by ranking service)

    Response fields per alert:
      id, location, lat, lon, title, message,
      severity, alert_type, source, created_at,
      distance_km, cpi, priority_score
    """
    response: list[dict] = []

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 1 — Geo-aware live data (Open-Meteo + USGS) — existing behaviour
    # ═══════════════════════════════════════════════════════════════════════
    if lat is not None and lon is not None:
        try:
            from ..services.live_data import get_real_time_alerts
            live_alerts = get_real_time_alerts(lat, lon)
            for a in live_alerts:
                response.append(_raw_to_response(a, lat_hint=lat, lon_hint=lon))
            logger.info("Alerts: live_data returned %d alerts", len(live_alerts))
        except Exception as exc:
            logger.error("Alerts: live_data fetch failed — %s", exc)

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 2 — Real Indian sources: INCOIS + IMD          [NEW / FEATURE FLAG]
    # ═══════════════════════════════════════════════════════════════════════
    if USE_REAL_DATA_SOURCES:
        try:
            real_indian = _get_real_indian_alerts()
            for a in real_indian:
                response.append(_raw_to_response(a, lat_hint=lat, lon_hint=lon))
            logger.info(
                "Alerts: real Indian sources added %d alerts (INCOIS+IMD)",
                len(real_indian),
            )
        except Exception as exc:
            logger.error("Alerts: real Indian sources block failed — %s", exc)

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 3 — Database alerts (community reports + persisted) — unchanged
    # ═══════════════════════════════════════════════════════════════════════
    db_alerts = db.query(Alert).all()

    if lat is not None and lon is not None:
        ranked_db = rank_alerts(db_alerts, lat, lon)
        for r in ranked_db:
            a = r["alert"]
            response.append({
                "id":             a.id,
                "location":       a.location,
                "lat":            a.lat,
                "lon":            a.lon,
                "title":          a.title,
                "message":        a.message,
                "severity":       a.severity,
                "alert_type":     a.alert_type,
                "source":         a.source,
                "created_at":     a.created_at,
                "distance_km":    r["distance_km"],
                "cpi":            r["cpi"],
                "priority_score": r["priority_score"],
            })
    else:
        for a in db_alerts:
            response.append({
                "id":             a.id,
                "location":       a.location,
                "lat":            a.lat,
                "lon":            a.lon,
                "title":          a.title,
                "message":        a.message,
                "severity":       a.severity,
                "alert_type":     a.alert_type,
                "source":         a.source,
                "created_at":     a.created_at,
                "distance_km":    0,
                "cpi":            0,
                "priority_score": 0,
            })

    # ═══════════════════════════════════════════════════════════════════════
    # Sort: High severity first, then by priority_score descending
    # ═══════════════════════════════════════════════════════════════════════
    response.sort(
        key=lambda x: (
            0 if x["severity"] == "High" else (1 if x["severity"] == "Medium" else 2),
            -x.get("priority_score", 0),
        )
    )

    return response


# ── Heatmap endpoint (unchanged) ──────────────────────────────────────────────

@router.get("/heatmap")
def get_heatmap_data():
    from ..ai_logic import generate_heatmap_data
    return generate_heatmap_data()
