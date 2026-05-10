"""
sar_fetcher.py — Sentinel-1 GRD SAR image fetcher via Copernicus Data Space Ecosystem (CDSE)

API: Sentinel Hub Process API  
Docs: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/
Auth: OAuth2 Client Credentials (register at https://dataspace.copernicus.eu)

SETUP:
  1. Register a free account at https://dataspace.copernicus.eu
  2. Go to Dashboard → User Settings → OAuth clients → Create
  3. Save CLIENT_ID and CLIENT_SECRET in your .env file

COST: Free tier includes 30,000 processing units/month (~1000+ SAR image fetches).
"""

import os
import io
import math
import requests
import numpy as np
import cv2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Evalscript: returns single-channel VV backscatter, log-scaled to 0–255.
# VV polarisation is standard for oil-spill detection (C-band, IW mode).
# Oil dampens capillary waves → lower backscatter → appears dark in VV.
SAR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["VV"],
      units: "LINEAR_POWER"
    }],
    output: {
      bands: 3,
      sampleType: "UINT8"
    }
  };
}

function evaluatePixel(sample) {
  // Log-transform: Maps linear power backscatter to [0,1] via log scale.
  // We use a wider range [-8, 0] to ensure calm sea (low backscatter) is visible.
  // -8.0 natural log is approx -34 dB, which captures almost all sea states.
  var epsilon = 1e-6;
  var logVV = Math.log(sample.VV + epsilon);
  var normalized = Math.max(0, Math.min(1, (logVV + 8.0) / 8.0));
  var pixel = Math.round(normalized * 255);
  return [pixel, pixel, pixel]; 
}
"""


def _get_access_token(client_id: str, client_secret: str) -> str:
    """Fetch OAuth2 access token from CDSE identity server."""
    resp = requests.post(
        CDSE_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _lat_lon_to_bbox(lat: float, lon: float, radius_km: float = 25.0):
    """
    Convert a centre lat/lon to a bounding box of ±radius_km.

    radius_km should be 20–50 km for a meaningful SAR patch.
    Returns [min_lon, min_lat, max_lon, max_lat] in WGS84.
    """
    # 1 degree latitude ≈ 111.32 km
    delta_lat = radius_km / 111.32
    # 1 degree longitude varies with latitude
    delta_lon = radius_km / (111.32 * math.cos(math.radians(lat)))
    return [
        round(lon - delta_lon, 6),
        round(lat - delta_lat, 6),
        round(lon + delta_lon, 6),
        round(lat + delta_lat, 6),
    ]


def fetch_sar_image(
    lat: float,
    lon: float,
    radius_km: float = 25.0,
    days_back: int = 30,
    image_size: int = 256,
) -> tuple[np.ndarray | None, dict]:
    """
    Fetch the most recent Sentinel-1 GRD SAR image for a location.

    Parameters
    ----------
    lat, lon    : centre coordinates (WGS84 decimal degrees)
    radius_km   : half-width of the bounding box in kilometres (default 25 km)
    days_back   : how many days back to search for imagery (default 30 days)
    image_size  : output pixel dimensions (default 256 to match CNN input)

    Returns
    -------
    image_array : np.ndarray of shape (256, 256, 3) normalised to [0, 1],
                  or None if no image found / API error.
    metadata    : dict with keys: bbox, date_range, status, error (if any)
    """
    client_id = os.getenv("CDSE_CLIENT_ID")
    client_secret = os.getenv("CDSE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None, {
            "status": "missing_credentials",
            "error": (
                "CDSE_CLIENT_ID and CDSE_CLIENT_SECRET not set. "
                "Register at https://dataspace.copernicus.eu and add credentials to .env"
            ),
        }

    bbox = _lat_lon_to_bbox(lat, lon, radius_km)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV",   # Dual VV+VH; we only use VV in evalscript
                        "resolution": "HIGH",
                        "mosaickingOrder": "mostRecent",
                    },
                    "processing": {
                        "backCoeff": "SIGMA0_ELLIPSOID",
                        "orthorectify": True,
                        "demInstance": "COPERNICUS",
                    },
                }
            ],
        },
        "output": {
            "width": image_size,
            "height": image_size,
            "responses": [
                {"identifier": "default", "format": {"type": "image/jpeg", "quality": 95}}
            ],
        },
        "evalscript": SAR_EVALSCRIPT,
    }

    try:
        token = _get_access_token(client_id, client_secret)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/jpeg",
        }
        resp = requests.post(
            CDSE_PROCESS_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )

        if resp.status_code == 200:
            img_array = np.frombuffer(resp.content, np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # BGR uint8
            if image is None:
                return None, {"status": "decode_error", "error": "Could not decode JPEG from API"}

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # The image from the evalscript is already log-transformed and mapped to 0-255.
            # We normalize to [0, 1] for the model, ensuring we don't 'double-log' 
            # which would make the ocean appear black.
            normalized = image_rgb.astype(np.float32) / 255.0
            resized = cv2.resize(normalized, (image_size, image_size))

            return resized, {
                "status": "success",
                "bbox": bbox,
                "date_range": {
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                },
                "image_size": image_size,
                "raw_jpeg_bytes": len(resp.content),
            }

        elif resp.status_code == 404:
            return None, {
                "status": "no_data",
                "error": f"No Sentinel-1 data found for this location/timeframe. "
                         f"Try increasing days_back (current: {days_back}).",
                "bbox": bbox,
            }
        else:
            return None, {
                "status": "api_error",
                "error": f"CDSE API returned HTTP {resp.status_code}: {resp.text[:300]}",
                "bbox": bbox,
            }

    except requests.exceptions.Timeout:
        return None, {"status": "timeout", "error": "CDSE API request timed out (60s)"}
    except requests.exceptions.RequestException as e:
        return None, {"status": "network_error", "error": str(e)}


def get_sar_image_as_jpeg_bytes(
    lat: float, lon: float, radius_km: float = 25.0, days_back: int = 30
) -> tuple[bytes | None, dict]:
    """
    Like fetch_sar_image(), but returns raw JPEG bytes for direct serving to the
    frontend (for preview display) instead of a numpy array.
    """
    client_id = os.getenv("CDSE_CLIENT_ID")
    client_secret = os.getenv("CDSE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None, {
            "status": "missing_credentials",
            "error": "CDSE credentials not configured.",
        }

    bbox = _lat_lon_to_bbox(lat, lon, radius_km)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV",
                        "resolution": "HIGH",
                        "mosaickingOrder": "mostRecent",
                    },
                    "processing": {
                        "backCoeff": "SIGMA0_ELLIPSOID",
                        "orthorectify": True,
                    },
                }
            ],
        },
        "output": {
            "width": 512,  # Higher res for preview
            "height": 512,
            "responses": [{"identifier": "default", "format": {"type": "image/jpeg", "quality": 90}}],
        },
        "evalscript": SAR_EVALSCRIPT,
    }

    try:
        token = _get_access_token(client_id, client_secret)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/jpeg",
        }
        resp = requests.post(CDSE_PROCESS_URL, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            return resp.content, {
                "status": "success",
                "bbox": bbox,
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d"),
            }
        else:
            return None, {
                "status": "api_error",
                "error": f"HTTP {resp.status_code}",
                "bbox": bbox,
            }
    except Exception as e:
        return None, {"status": "error", "error": str(e)}