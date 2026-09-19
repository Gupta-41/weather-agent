from backend.alerts.messages import render, render_all
from backend.alerts.rules import evaluate_day, evaluate_forecast, fingerprint
from backend.tools.alerts import check_alerts, get_weather_alerts


def day(**overrides):
    base = {
        "date": "2026-09-20",
        "weather_code": 2,
        "condition": "Partly cloudy",
        "temp_max": 30.0,
        "temp_min": 22.0,
        "precipitation_sum": 0.0,
        "wind_speed_max": 10.0,
    }
    return {**base, **overrides}


def codes(alerts):
    return {a["code"] for a in alerts}


def test_calm_day_raises_nothing():
    assert evaluate_day(day()) == []


def test_rainfall_bands_pick_the_highest_one_cleared():
    assert codes(evaluate_day(day(precipitation_sum=70))) == {"heavy_rain"}
    assert codes(evaluate_day(day(precipitation_sum=130))) == {"very_heavy_rain"}
    assert codes(evaluate_day(day(precipitation_sum=250))) == {
        "extremely_heavy_rain"
    }


def test_rain_just_below_threshold_is_not_an_alert():
    assert evaluate_day(day(precipitation_sum=64.4)) == []


def test_heat_and_cold_use_opposite_directions():
    assert codes(evaluate_day(day(temp_max=46))) == {"severe_heat"}
    assert codes(evaluate_day(day(temp_min=3))) == {"severe_cold"}
    assert codes(evaluate_day(day(temp_min=8))) == {"cold"}


def test_wind_and_hail_can_fire_on_the_same_day():
    found = codes(evaluate_day(day(wind_speed_max=95, weather_code=96)))
    assert found == {"storm_wind", "hailstorm"}


def test_one_alert_per_metric_per_day():
    alerts = evaluate_day(day(precipitation_sum=250))
    assert len([a for a in alerts if a["metric"] == "precipitation_sum"]) == 1


def test_forecast_alerts_sort_most_severe_first():
    forecast = {
        "location": {"name": "Hyderabad"},
        "days": [
            day(date="2026-09-19", temp_min=8),  # advisory
            day(date="2026-09-20", precipitation_sum=250),  # warning
        ],
    }
    alerts = evaluate_forecast(forecast)
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["location"] == "Hyderabad"


def test_fingerprint_changes_when_severity_is_upgraded():
    watch = {"code": "gale", "severity": "watch", "date": "2026-09-20"}
    warning = {**watch, "severity": "warning"}
    assert fingerprint(1, watch) != fingerprint(1, warning)


def test_render_fills_the_template_and_labels_severity():
    alert = {
        "code": "very_heavy_rain",
        "severity": "watch",
        "date": "2026-09-20",
        "value": 130.0,
        "unit": "mm",
        "location": "Hyderabad",
    }
    rendered = render(alert, "en")
    assert "Hyderabad" in rendered["headline"]
    assert "130.0 mm" in rendered["advice"]
    assert rendered["severity_label"] == "Watch"


def test_render_translates_and_unknown_language_falls_back_to_english():
    alert = {
        "code": "heat",
        "severity": "advisory",
        "date": "2026-05-01",
        "value": 42.0,
        "unit": "°C",
        "location": "Nagpur",
    }
    hindi = render(alert, "hi")
    assert hindi["severity_label"] == "सूचना"
    assert "Hot day" not in hindi["headline"]

    telugu = render(alert, "te")
    assert telugu["language"] == "te"

    unsupported = render(alert, "fr")
    assert unsupported["headline"].startswith("Hot day")
    assert unsupported["language"] == "en"


def test_render_all_keeps_order():
    alerts = [
        {"code": "heat", "severity": "advisory", "date": "d", "value": 41, "unit": "°C"},
        {"code": "cold", "severity": "advisory", "date": "d", "value": 5, "unit": "°C"},
    ]
    assert [a["code"] for a in render_all(alerts, "en")] == ["heat", "cold"]


async def test_check_alerts_reads_the_forecast(severe_http):
    result = await check_alerts(severe_http, "Paris", days=3)
    assert codes(result["alerts"]) == {
        "severe_heat",
        "storm_wind",
        "hailstorm",
        "very_heavy_rain",
        "severe_cold",
    }


async def test_alert_tool_attaches_text_and_a_summary(severe_http):
    result = await get_weather_alerts(severe_http, "Paris", days=3, language="en")
    assert "highest severity is warning" in result["summary"]
    assert all(a["headline"] for a in result["alerts"])


async def test_alert_tool_reports_quiet_weather(http):
    result = await get_weather_alerts(http, "Paris", days=2)
    assert result["alerts"] == []
    assert "No severe weather" in result["summary"]
