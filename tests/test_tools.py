import pytest

from backend.tools.current import get_current_weather
from backend.tools.forecast import get_forecast
from backend.tools.geocode import LocationNotFound, geocode
from backend.tools.registry import ToolError, run_tool


async def test_geocode_uses_country_hint(http):
    result = await geocode(http, "Paris, France")
    assert result["country"] == "France"


async def test_geocode_without_hint_takes_first_result(http):
    result = await geocode(http, "Paris")
    assert result["country"] == "United States"


async def test_geocode_not_found(http):
    with pytest.raises(LocationNotFound):
        await geocode(http, "Nowhereville")


async def test_current_weather_shape(http):
    data = await get_current_weather(http, "Paris, France")
    assert data["location"]["country"] == "France"
    assert data["condition"] == "Partly cloudy"
    assert data["temperature"] == 24.5
    assert data["units"]["temperature"] == "°C"
    assert data["is_day"] is True


async def test_current_weather_imperial_labels(http):
    data = await get_current_weather(http, "Paris", units="imperial")
    assert data["units"]["temperature"] == "°F"


async def test_current_weather_rejects_bad_units(http):
    with pytest.raises(ValueError):
        await get_current_weather(http, "Paris", units="kelvin")


async def test_forecast_shape(http):
    data = await get_forecast(http, "Paris", days=2)
    assert [d["date"] for d in data["days"]] == ["2026-09-19", "2026-09-20"]
    assert data["days"][1]["condition"] == "Slight rain"
    assert data["days"][1]["precipitation_probability_max_percent"] == 80


async def test_unknown_tool(http):
    with pytest.raises(ToolError):
        await run_tool("get_horoscope", {}, http)
