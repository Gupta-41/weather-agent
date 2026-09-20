import httpx

from backend.tools.geocode import geocode
from backend.tools.openmeteo import FORECAST_URL, get_with_retry, location_summary
from backend.units import unit_system
from backend.weather_codes import describe

CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "is_day",
]


async def get_current_weather(
    client: httpx.AsyncClient, location: str, units: str = "metric"
) -> dict:
    system = unit_system(units)
    loc = await geocode(client, location)

    resp = await get_with_retry(
        client,
        FORECAST_URL,
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "current": ",".join(CURRENT_FIELDS),
            "timezone": "auto",
            **system["api"],
        },
    )
    cur = resp.json()["current"]

    return {
        "location": location_summary(loc),
        "units": system["labels"],
        "observed_at": cur["time"],
        "condition": describe(cur.get("weather_code")),
        "temperature": cur.get("temperature_2m"),
        "feels_like": cur.get("apparent_temperature"),
        "humidity_percent": cur.get("relative_humidity_2m"),
        "precipitation": cur.get("precipitation"),
        "cloud_cover_percent": cur.get("cloud_cover"),
        "wind_speed": cur.get("wind_speed_10m"),
        "wind_direction_degrees": cur.get("wind_direction_10m"),
        "is_day": bool(cur.get("is_day")),
    }
