UNIT_SYSTEMS = {
    "metric": {
        "api": {
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        },
        "labels": {"temperature": "°C", "wind_speed": "km/h", "precipitation": "mm"},
    },
    "imperial": {
        "api": {
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        },
        "labels": {"temperature": "°F", "wind_speed": "mph", "precipitation": "in"},
    },
}


def unit_system(units: str) -> dict:
    if units not in UNIT_SYSTEMS:
        raise ValueError(f"units must be one of: {', '.join(UNIT_SYSTEMS)}")
    return UNIT_SYSTEMS[units]
