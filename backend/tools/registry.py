"""Tool definitions (Anthropic tool-use format) and dispatch.

To add a tool: write the async function, add a definition below, and register
it in _TOOLS. The agent and the Tool Selection Trace pick it up with no other
changes.

Descriptions are written to be discriminative — each says what the tool is for
*and* what to reach for instead — because tool-selection quality is what this
project is judged on, and the description is where that quality is decided.
"""

import httpx

from backend.tools.alerts import get_weather_alerts
from backend.tools.current import get_current_weather
from backend.tools.forecast import get_forecast
from backend.tools.history import get_climate_trend, get_historical_weather

LOCATION_DESCRIPTION = (
    "City or place name, optionally followed by a region or country to "
    "disambiguate, e.g. 'Hyderabad' or 'Paris, France'."
)

UNITS_PROPERTY = {
    "type": "string",
    "enum": ["metric", "imperial"],
    "description": "metric = °C, km/h, mm. imperial = °F, mph, in.",
    "default": "metric",
}

TOOL_DEFINITIONS = [
    {
        "name": "get_current_weather",
        "description": (
            "Get the weather conditions right now for a place: temperature, "
            "feels-like temperature, sky condition, humidity, wind and "
            "precipitation. Use for questions about the present moment. "
            "Do not use for tomorrow or any future day."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": LOCATION_DESCRIPTION},
                "units": UNITS_PROPERTY,
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_forecast",
        "description": (
            "Get a day-by-day forecast for a place, starting today, for up to "
            "16 days: high and low temperature, sky condition, rain chance and "
            "amount, max wind, sunrise and sunset. Use for tomorrow, the "
            "weekend, next week, or planning questions. Not for right-now "
            "conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": LOCATION_DESCRIPTION},
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 16,
                    "description": "Number of days including today.",
                    "default": 5,
                },
                "units": UNITS_PROPERTY,
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_weather_alerts",
        "description": (
            "Check whether a place crosses a severe-weather threshold in the "
            "next few days — heavy rain, heat, cold, high wind, thunderstorm "
            "or hail — and return ready-written warnings with safety advice. "
            "Use when the user asks whether it is safe, whether there is a "
            "warning, or whether a storm is coming. Use get_forecast instead "
            "for ordinary 'what will the weather be' questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": LOCATION_DESCRIPTION},
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 16,
                    "description": "How many days ahead to check.",
                    "default": 5,
                },
                "language": {
                    "type": "string",
                    "description": (
                        "Two-letter code for the alert wording, e.g. 'en', "
                        "'hi', 'te'. Use the language the user is writing in."
                    ),
                    "default": "en",
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_historical_weather",
        "description": (
            "Get observed past weather for a date range, with a summary of the "
            "period: mean high and low, hottest and coldest day, total rainfall "
            "and number of rain days. Use for questions about what the weather "
            "actually was — last month, last monsoon, a specific past date. "
            "The archive lags about five days, so use get_forecast for today, "
            "yesterday and the day before. For multi-year questions use "
            "get_climate_trend instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": LOCATION_DESCRIPTION},
                "start_date": {
                    "type": "string",
                    "description": "First day of the range, YYYY-MM-DD.",
                },
                "end_date": {
                    "type": "string",
                    "description": "Last day of the range, YYYY-MM-DD.",
                },
                "units": UNITS_PROPERTY,
            },
            "required": ["location", "start_date", "end_date"],
        },
    },
    {
        "name": "get_climate_trend",
        "description": (
            "Get how one calendar month has changed at a place across many "
            "years: the mean high, mean low and total rainfall for that month "
            "in each year, plus a per-decade trend. Use for questions about "
            "whether somewhere is getting hotter, drier or wetter over time, "
            "or comparing one month across years. Use get_historical_weather "
            "instead for a single date range."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": LOCATION_DESCRIPTION},
                "month": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                    "description": "Calendar month to compare, 1 = January.",
                },
                "start_year": {
                    "type": "integer",
                    "description": "First year of the comparison, e.g. 1995.",
                },
                "end_year": {
                    "type": "integer",
                    "description": "Last year of the comparison, e.g. 2025.",
                },
                "units": UNITS_PROPERTY,
            },
            "required": ["location", "month", "start_year", "end_year"],
        },
    },
]

_TOOLS = {
    "get_current_weather": get_current_weather,
    "get_forecast": get_forecast,
    "get_weather_alerts": get_weather_alerts,
    "get_historical_weather": get_historical_weather,
    "get_climate_trend": get_climate_trend,
}

TOOL_NAMES = [t["name"] for t in TOOL_DEFINITIONS]


class ToolError(Exception):
    pass


async def run_tool(name: str, tool_input: dict, client: httpx.AsyncClient) -> dict:
    func = _TOOLS.get(name)
    if func is None:
        raise ToolError(f"Unknown tool: {name}")
    return await func(client, **tool_input)
