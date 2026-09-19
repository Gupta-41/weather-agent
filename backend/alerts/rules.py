"""Turn a forecast into severe-weather alerts.

Thresholds follow India Meteorological Department colour-code practice where a
public number exists — the 24-hour rainfall bands are IMD's, and 62 km/h is
IMD's gale threshold. Heat and cold use absolute values rather than IMD's
departure-from-normal method, because departure needs a climatological normal
we don't fetch here; the numbers chosen are the ones IMD's plains heat-wave
criteria start from.

Rules run on **metric** forecast data. Callers must request metric units.
"""

SEVERITIES = ("advisory", "watch", "warning")
SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITIES)}

# (metric, threshold, code, severity, unit) — evaluated low to high.
RAINFALL_BANDS = [
    (64.5, "heavy_rain", "advisory"),
    (115.6, "very_heavy_rain", "watch"),
    (204.5, "extremely_heavy_rain", "warning"),
]

HEAT_BANDS = [
    (40.0, "heat", "advisory"),
    (45.0, "severe_heat", "warning"),
]

WIND_BANDS = [
    (50.0, "strong_wind", "advisory"),
    (62.0, "gale", "watch"),
    (88.0, "storm_wind", "warning"),
]

COLD_BANDS = [
    (10.0, "cold", "advisory"),
    (4.0, "severe_cold", "watch"),
]

THUNDERSTORM_CODES = {
    95: ("thunderstorm", "watch"),
    96: ("hailstorm", "warning"),
    99: ("hailstorm", "warning"),
}


def _highest_band(value, bands, unit, metric):
    """Bands are ascending: the last one the value clears wins."""
    if value is None:
        return None
    hit = None
    for threshold, code, severity in bands:
        if value >= threshold:
            hit = (code, severity, threshold)
    if hit is None:
        return None
    code, severity, threshold = hit
    return {
        "code": code,
        "severity": severity,
        "metric": metric,
        "value": round(float(value), 1),
        "threshold": threshold,
        "unit": unit,
    }


def _lowest_band(value, bands, unit, metric):
    """Cold bands are descending thresholds: the last one cleared wins."""
    if value is None:
        return None
    hit = None
    for threshold, code, severity in bands:
        if value <= threshold:
            hit = (code, severity, threshold)
    if hit is None:
        return None
    code, severity, threshold = hit
    return {
        "code": code,
        "severity": severity,
        "metric": metric,
        "value": round(float(value), 1),
        "threshold": threshold,
        "unit": unit,
    }


def evaluate_day(day: dict) -> list[dict]:
    """All alerts triggered by one forecast day. At most one per metric."""
    found = [
        _highest_band(
            day.get("precipitation_sum"), RAINFALL_BANDS, "mm", "precipitation_sum"
        ),
        _highest_band(day.get("temp_max"), HEAT_BANDS, "°C", "temp_max"),
        _highest_band(day.get("wind_speed_max"), WIND_BANDS, "km/h", "wind_speed_max"),
        _lowest_band(day.get("temp_min"), COLD_BANDS, "°C", "temp_min"),
    ]

    code = day.get("weather_code")
    if code is not None and int(code) in THUNDERSTORM_CODES:
        name, severity = THUNDERSTORM_CODES[int(code)]
        found.append(
            {
                "code": name,
                "severity": severity,
                "metric": "weather_code",
                "value": int(code),
                "threshold": None,
                "unit": None,
            }
        )

    alerts = [a for a in found if a]
    for alert in alerts:
        alert["date"] = day.get("date")
        alert["condition"] = day.get("condition")
    return alerts


def evaluate_forecast(forecast: dict, max_days: int | None = None) -> list[dict]:
    """Alerts across a forecast, most severe first, then soonest."""
    days = forecast.get("days") or []
    if max_days is not None:
        days = days[:max_days]

    alerts = []
    for day in days:
        alerts.extend(evaluate_day(day))

    place = forecast.get("location") or {}
    for alert in alerts:
        alert["location"] = place.get("name")

    alerts.sort(key=lambda a: (-SEVERITY_RANK[a["severity"]], a["date"] or ""))
    return alerts


def fingerprint(location_id: int, alert: dict) -> str:
    """Identity of an alert, so re-running the scheduler doesn't duplicate it.

    Severity is part of it on purpose: if a watch is upgraded to a warning for
    the same day, that is a new alert the user should see.
    """
    return f"{location_id}|{alert['code']}|{alert['severity']}|{alert['date']}"
