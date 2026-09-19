import os
from types import SimpleNamespace

# Set before anything imports backend.config, which reads the environment once.
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("ALERTS_ENABLED", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import httpx  # noqa: E402
import pytest  # noqa: E402


def weather_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "geocoding-api.open-meteo.com" in url:
        name = request.url.params["name"]
        if name == "Nowhereville":
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Paris",
                        "country": "United States",
                        "country_code": "US",
                        "admin1": "Texas",
                        "latitude": 33.66,
                        "longitude": -95.55,
                        "timezone": "America/Chicago",
                    },
                    {
                        "name": "Paris",
                        "country": "France",
                        "country_code": "FR",
                        "admin1": "Île-de-France",
                        "latitude": 48.85,
                        "longitude": 2.35,
                        "timezone": "Europe/Paris",
                    },
                ]
            },
        )
    if "archive-api.open-meteo.com" in url:
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": [
                        "2023-06-01", "2023-06-02", "2023-06-03",
                        "2024-06-01", "2024-06-02", "2024-06-03",
                        "2025-06-01", "2025-06-02", "2025-06-03",
                    ],
                    "weather_code": [2, 61, 0, 2, 61, 0, 2, 61, 0],
                    "temperature_2m_max": [
                        34.0, 30.0, 35.0,
                        35.0, 31.0, 36.0,
                        36.0, 32.0, 37.0,
                    ],
                    "temperature_2m_min": [
                        24.0, 23.0, 25.0,
                        25.0, 24.0, 26.0,
                        26.0, 25.0, 27.0,
                    ],
                    "temperature_2m_mean": [
                        29.0, 26.5, 30.0,
                        30.0, 27.5, 31.0,
                        31.0, 28.5, 32.0,
                    ],
                    "precipitation_sum": [
                        0.0, 12.0, 0.0,
                        0.0, 10.0, 0.0,
                        0.0, 8.0, 0.0,
                    ],
                }
            },
        )
    if "api.open-meteo.com" in url:
        return httpx.Response(
            200,
            json={
                "current": {
                    "time": "2026-09-19T14:00",
                    "temperature_2m": 24.5,
                    "apparent_temperature": 26.0,
                    "relative_humidity_2m": 60,
                    "precipitation": 0.0,
                    "weather_code": 2,
                    "cloud_cover": 40,
                    "wind_speed_10m": 11.2,
                    "wind_direction_10m": 250,
                    "is_day": 1,
                },
                "daily": {
                    "time": ["2026-09-19", "2026-09-20"],
                    "weather_code": [2, 61],
                    "temperature_2m_max": [27.0, 22.0],
                    "temperature_2m_min": [17.0, 15.0],
                    "precipitation_sum": [0.0, 4.2],
                    "precipitation_probability_max": [5, 80],
                    "wind_speed_10m_max": [15.0, 20.0],
                    "sunrise": ["2026-09-19T06:52", "2026-09-20T06:53"],
                    "sunset": ["2026-09-19T19:30", "2026-09-20T19:28"],
                },
            },
        )
    return httpx.Response(404)


@pytest.fixture
async def http():
    async with httpx.AsyncClient(transport=httpx.MockTransport(weather_handler)) as client:
        yield client


# --- fake Anthropic client -------------------------------------------------


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(tool_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)


def llm_response(content, stop_reason):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )


class FakeLLM:
    """Returns scripted responses, one per messages.create call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = self

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def severe_handler(request: httpx.Request) -> httpx.Response:
    """Same geocoder, but a forecast that crosses several alert thresholds."""
    url = str(request.url)
    if "geocoding-api.open-meteo.com" in url:
        return weather_handler(request)
    if "api.open-meteo.com" in url:
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-09-19", "2026-09-20", "2026-09-21"],
                    "weather_code": [96, 61, 2],
                    "temperature_2m_max": [46.0, 30.0, 28.0],
                    "temperature_2m_min": [28.0, 24.0, 3.0],
                    "precipitation_sum": [0.0, 130.0, 1.0],
                    "precipitation_probability_max": [10, 95, 20],
                    "wind_speed_10m_max": [95.0, 40.0, 12.0],
                    "sunrise": ["2026-09-19T06:00"] * 3,
                    "sunset": ["2026-09-19T18:30"] * 3,
                }
            },
        )
    return httpx.Response(404)


@pytest.fixture
async def severe_http():
    transport = httpx.MockTransport(severe_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        yield client


@pytest.fixture
def conn():
    from backend import db as db_module

    connection = db_module.connect(":memory:")
    db_module.init(connection)
    yield connection
    connection.close()
