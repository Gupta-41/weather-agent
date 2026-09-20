import httpx

from backend.tools.openmeteo import GEOCODE_URL, get_with_retry


class LocationNotFound(Exception):
    pass


def _matches_hint(result: dict, hint: str) -> bool:
    if hint == (result.get("country_code") or "").lower():
        return True
    if len(hint) < 3:
        return False
    return hint in (result.get("country") or "").lower() or hint in (
        result.get("admin1") or ""
    ).lower()


async def geocode(client: httpx.AsyncClient, location: str) -> dict:
    """Resolve a place name like 'Paris, France' to coordinates.

    Open-Meteo's geocoder searches on the place name only, so anything after
    the first comma is used to pick between same-named places.
    """
    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")

    name, _, hint = location.partition(",")
    name, hint = name.strip(), hint.strip().lower()

    resp = await get_with_retry(
        client,
        GEOCODE_URL,
        params={
            "name": name,
            "count": 10 if hint else 1,
            "language": "en",
            "format": "json",
        },
    )
    results = resp.json().get("results") or []
    if not results:
        raise LocationNotFound(f"No location found for '{location}'")

    chosen = results[0]
    if hint:
        chosen = next((r for r in results if _matches_hint(r, hint)), results[0])
    return chosen
