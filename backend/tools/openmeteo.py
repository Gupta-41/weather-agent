GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def location_summary(loc: dict) -> dict:
    return {
        "name": loc["name"],
        "region": loc.get("admin1"),
        "country": loc.get("country"),
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "timezone": loc.get("timezone"),
    }
