"""The alert check, exposed as a tool the agent can choose.

The same function backs the background scheduler, so a proactive alert and an
alert the user asked for are produced by identical logic — there is no second
code path to keep in sync.
"""

import httpx

from backend.alerts.rules import evaluate_forecast
from backend.tools.forecast import get_forecast

ALERT_WINDOW_DAYS = 5


async def check_alerts(
    client: httpx.AsyncClient, location: str, days: int = ALERT_WINDOW_DAYS
) -> dict:
    """Raw alert objects for a place. Alerts are always evaluated in metric."""
    days = max(1, min(int(days), 16))
    forecast = await get_forecast(client, location, days=days, units="metric")
    alerts = evaluate_forecast(forecast)
    return {"location": forecast["location"], "days_checked": days, "alerts": alerts}


async def get_weather_alerts(
    client: httpx.AsyncClient,
    location: str,
    days: int = ALERT_WINDOW_DAYS,
    language: str = "en",
) -> dict:
    """Tool entry point: alerts with headline and advice text attached."""
    from backend.alerts.messages import render_all

    result = await check_alerts(client, location, days)
    result["alerts"] = render_all(result["alerts"], language)
    if not result["alerts"]:
        result["summary"] = (
            f"No severe weather thresholds are crossed in the next {days} days."
        )
    else:
        highest = result["alerts"][0]["severity"]
        result["summary"] = (
            f"{len(result['alerts'])} alert(s); highest severity is {highest}."
        )
    return result
