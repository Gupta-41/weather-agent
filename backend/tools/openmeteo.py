import asyncio

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
RETRY_BASE_DELAY = 0.6


async def get_with_retry(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    """GET with a short retry-and-backoff on rate limits and transient errors.

    Open-Meteo's free tier occasionally rate-limits a shared server IP (like
    Render's) under repeated testing, and its servers have brief blips like
    any other API. Without this, a single transient 429/503 bubbles straight
    up to the agent, which then has to tell the user it "couldn't get the
    data" — technically honest, but avoidable. One retry clears it almost
    every time; a network-level failure (no response at all) gets the same
    treatment since it's just as likely to be transient.
    """
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))
    raise last_exc  # pragma: no cover — unreachable, satisfies type checkers


def location_summary(loc: dict) -> dict:
    return {
        "name": loc["name"],
        "region": loc.get("admin1"),
        "country": loc.get("country"),
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "timezone": loc.get("timezone"),
    }
