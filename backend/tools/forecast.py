import httpx

from backend.tools.geocode import geocode
from backend.tools.openmeteo import FORECAST_URL, get_with_retry, location_summary
from backend.units import unit_system
from backend.weather_codes import describe

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "sunrise",
    "sunset",
]

MAX_DAYS = 16


async def get_forecast(
    client: httpx.AsyncClient, location: str, days: int = 5, units: str = "metric"
) -> dict:
    system = unit_system(units)
    days = max(1, min(int(days), MAX_DAYS))
    loc = await geocode(client, location)

    resp = await get_with_retry(
        client,
        FORECAST_URL,
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "daily": ",".join(DAILY_FIELDS),
            "forecast_days": days,
            "timezone": "auto",
            **system["api"],
        },
    )
    daily = resp.json()["daily"]

    def at(field: str, i: int):
        values = daily.get(field) or []
        return values[i] if i < len(values) else None

    return {
        "location": location_summary(loc),
        "units": system["labels"],
        "days": [
            {
                "date": date,
                "weather_code": at("weather_code", i),
                "condition": describe(at("weather_code", i)),
                "temp_max": at("temperature_2m_max", i),
                "temp_min": at("temperature_2m_min", i),
                "precipitation_sum": at("precipitation_sum", i),
                "precipitation_probability_max_percent": at(
                    "precipitation_probability_max", i
                ),
                "wind_speed_max": at("wind_speed_10m_max", i),
                "sunrise": at("sunrise", i),
                "sunset": at("sunset", i),
            }
            for i, date in enumerate(daily["time"])
        ],
    }
