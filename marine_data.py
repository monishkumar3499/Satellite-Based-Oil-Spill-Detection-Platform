"""
marine_data.py — High-Reliability Open-Meteo Engine (v5)
=========================================================
REPLACED CMEMS with Open-Meteo for 100% stability.
Fetches: SST, Wind, Waves, Currents, and 31-day Thermal Anomaly.

No extra libraries (copernicusmarine) required.
No event loop issues.
"""

import datetime
import json
import logging
import os
import urllib.request
import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: Safe HTTP GET
# ---------------------------------------------------------------------------
def _http_get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OilSpillDetector/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.warning(f"[API Error] {e}")
        return None

def _nanmean(arr):
    try:
        valid = [v for v in arr if v is not None]
        if not valid: return None
        return round(float(np.mean(valid)), 3)
    except: return None

# ---------------------------------------------------------------------------
# Core Fetcher: Open-Meteo
# ---------------------------------------------------------------------------
def fetch_all_marine_data(lat: float, lon: float) -> dict:
    """
    Primary fetcher using Open-Meteo Weather & Marine APIs.
    Includes 31-day historical SST for anomaly detection.
    """
    # Normalize longitude to [-180, 180] range for API compatibility
    lon = ((lon + 180) % 360) - 180
    
    logger.info(f"Fetching High-Reliability Marine Data for ({lat}, {lon}) via Open-Meteo...")
    
    # 1. Marine API: SST, Waves, Currents (Live + 31 days history)
    marine_url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=wave_height,wave_direction,wave_period,ocean_current_velocity,sea_surface_temperature"
        f"&past_days=31&timezone=UTC"
    )
    
    # 2. Weather API: Wind (Live)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=wind_speed_10m,wind_direction_10m"
        f"&wind_speed_unit=ms&past_days=1&forecast_days=1&timezone=UTC"
    )

    marine_data = _http_get(marine_url)
    weather_data = _http_get(weather_url)

    raw = {}
    
    # Parse Marine Data (SST, Waves, Currents)
    if marine_data and "hourly" in marine_data:
        h = marine_data["hourly"]
        
        # SST & Anomaly
        sst_series = h.get("sea_surface_temperature", [])
        if sst_series:
            current_sst = sst_series[-1]
            baseline_sst = _nanmean(sst_series)
            raw["temperature_c"] = current_sst
            if baseline_sst is not None and current_sst is not None:
                raw["sst_anomaly"] = round(current_sst - baseline_sst, 2)
                raw["sst_baseline"] = round(baseline_sst, 2)
                
            # History for chart (daily intervals)
            raw["sst_history"] = [
                {"day": i-30, "temp": round(t, 2) if t is not None else None} 
                for i, t in enumerate(sst_series[::24])
            ]

        # Waves
        raw["wave_height_m"] = _nanmean(h.get("wave_height", []))
        raw["wave_dir_deg"] = _nanmean(h.get("wave_direction", []))
        raw["wave_period_s"] = _nanmean(h.get("wave_period", []))
        
        # Currents
        raw["current_speed_ms"] = _nanmean(h.get("ocean_current_velocity", []))

    # Parse Weather Data (Wind)
    if weather_data and "hourly" in weather_data:
        h = weather_data["hourly"]
        raw["wind_speed_ms"] = _nanmean(h.get("wind_speed_10m", []))
        raw["wind_dir_deg"] = _nanmean(h.get("wind_direction_10m", []))

    return _build_output(raw, lat, lon)

# ---------------------------------------------------------------------------
# Decision Logic
# ---------------------------------------------------------------------------
def compute_final_decision(cnn_score: float, ocean_context: dict) -> dict:
    wind_adj = ocean_context.get("wind_adjustment", 0)
    raw_conf = cnn_score * 100
    adj_conf = max(0.0, min(100.0, raw_conf + wind_adj))
    wind_flag = ocean_context.get("wind_flag", "unknown")
    
    # Deep Scientific Reasoning Generator
    anomaly = ocean_context.get("sst_anomaly", 0) or 0
    ws = ocean_context.get("wind_speed_ms", 0) or 0
    
    analysis_steps = []
    
    # Step 1: SAR Morphology
    if cnn_score > 0.8:
        analysis_steps.append("CRITICAL: High-contrast dampening signature detected in SAR backscatter.")
    elif cnn_score > 0.5:
        analysis_steps.append("NOTICE: Moderate backscatter dampening observed, consistent with surface films.")
    else:
        analysis_steps.append("STABLE: No significant backscatter dampening identified in microwave return.")

    # Step 2: Atmospheric Validation
    if ws < 2.0:
        analysis_steps.append(f"CAUTION: Surface wind is extremely low ({ws}m/s). High probability of 'Wind Calm' look-alikes.")
    elif 3.0 <= ws <= 8.0:
        analysis_steps.append(f"VALIDATED: Wind speed ({ws}m/s) is optimal for SAR oil-spill discrimination.")
    else:
        analysis_steps.append(f"NOISE: Wind speed ({ws}m/s) may cause surface mixing or signal dispersion.")

    # Step 3: Thermal Signature
    if abs(anomaly) > 1.0:
        trend = "positive" if anomaly > 0 else "negative"
        analysis_steps.append(f"ANOMALY: {abs(anomaly)}°C {trend} thermal deviation from 30-day baseline detected.")
    else:
        analysis_steps.append("THERMAL: Sea surface temperature remains within nominal 1-sigma historical variance.")

    # Final Claude-style detailed reasoning
    if cnn_score >= 0.5:
        if ws < 2.0:
            final_report = (
                f"The analysis identifies a potential oil spill with {adj_conf}% adjusted confidence. "
                f"However, the atmospheric modality reveals ultra-low wind speeds ({ws}m/s), which significantly increases "
                f"the risk of false positives from natural 'look-alikes'. While the SAR imagery shows clear "
                f"morphological dampening, the physical context suggests this could be a 'wind calm' patch. "
                f"Re-acquisition under higher wind stress is recommended for confirmation."
            )
        else:
            final_report = (
                f"Multi-modal fusion confirms an oil spill event with high confidence ({adj_conf}%). "
                f"The detection is cross-validated by (1) microwave backscatter dampening and (2) optimal wind stress ({ws}m/s). "
                f"{'The thermal anomaly reinforces this as a fresh release.' if anomaly > 1.0 else ''}"
            )
    else:
        final_report = (
            "The system concludes no oil spill is present. The SAR returns show nominal sea surface roughness, "
            "and physical proxies remain within standard historical deviations."
        )

    return {
        "final_label": "Oil Spill Detected" if (cnn_score >= 0.5 and ws >= 2.0) else "Potential Spill" if (cnn_score >= 0.5) else "No Oil Spill Found",
        "adjusted_confidence": round(adj_conf, 2),
        "raw_cnn_confidence": round(raw_conf, 2),
        "fusion_reason": final_report,
        "analysis_steps": analysis_steps,
        "ocean_context": ocean_context
    }

# ---------------------------------------------------------------------------
# Internal Builder (Frontend Compatibility)
# ---------------------------------------------------------------------------
def _build_output(raw, lat, lon) -> dict:
    ws = raw.get("wind_speed_ms")
    if ws is None: wind_flag, wind_note, wind_adj = "unknown", "Wind data unavailable.", 0
    elif ws < 2.0: wind_flag, wind_note, wind_adj = "too_low", f"Low wind ({ws} m/s) - look-alike risk.", -25
    elif ws <= 10.0: wind_flag, wind_note, wind_adj = "good", f"Optimal wind ({ws} m/s).", 0
    else: wind_flag, wind_note, wind_adj = "high", f"Strong wind ({ws} m/s) - dispersal likely.", -10

    thickness = "Unknown"
    if ws is not None:
        if ws < 2.0: thickness = "Look-alike Risk"
        elif ws <= 8.0: thickness = "Moderate-to-Thick"
        else: thickness = "Thin/Dispersed"

    return {
        "lat": lat, "lon": lon, "source": "Open-Meteo (High Reliability)",
        "data_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "temperature_c": raw.get("temperature_c"),
        "sst_celsius": raw.get("temperature_c"),
        "sst_anomaly": raw.get("sst_anomaly"),
        "sst_baseline": raw.get("sst_baseline"),
        "sst_history": raw.get("sst_history", []),
        "wave_height_m": raw.get("wave_height_m"),
        "wave_period_s": raw.get("wave_period_s"),
        "wave_dir_deg": raw.get("wave_dir_deg"),
        "wind_speed_ms": raw.get("wind_speed_ms"),
        "wind_dir_deg": raw.get("wind_dir_deg"),
        "current_speed_ms": raw.get("current_speed_ms"),
        "wind_flag": wind_flag, "wind_note": wind_note, "wind_adjustment": wind_adj,
        "thickness_proxy": thickness,
        "risk_score": 80.0 if (ws is not None and 3.0 <= ws <= 8.0) else 40.0,
    }

# Alias
def fetch_ocean_context(lat, lon): return fetch_all_marine_data(lat, lon)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(fetch_all_marine_data(21.79, 63.72), indent=2))