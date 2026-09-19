"""Past weather and climate trends, from the Open-Meteo reanalysis archive.

Two tools, deliberately separate, because they answer different questions:

- get_historical_weather — what actually happened over one date range.
- get_climate_trend      — how one month has shifted across many years.

The archive lags real time by about five days, so "yesterday" is a forecast
question, not a historical one. The tool descriptions in the registry say so.
"""

from datetime import date, datetime

import httpx

from backend.tools.geocode import geocode
from backend.tools.openmeteo import ARCHIVE_URL, location_summary
from backend.units import unit_system
from backend.weather_codes import describe

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
]

ARCHIVE_START = date(1940, 1, 1)
MAX_RANGE_DAYS = 400
MAX_DAILY_ROWS = 31
MAX_TREND_YEARS = 50
RAIN_DAY_MM = 2.5


def _parse_date(value: str, field: str) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError(f"{field} must be a date in YYYY-MM-DD format") from None


def _mean(values):
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else None


def _total(values):
    clean = [v for v in values if v is not None]
    return round(sum(clean), 1) if clean else None


def _extreme(values, dates, pick):
    pairs = [(v, d) for v, d in zip(values, dates) if v is not None]
    if not pairs:
        return None
    value, day = pick(pairs, key=lambda p: p[0])
    return {"value": value, "date": day}


def _trend_per_decade(years: list[int], values: list[float]):
    """Ordinary least squares slope, scaled to change per decade."""
    pairs = [(y, v) for y, v in zip(years, values) if v is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    mean_x = sum(p[0] for p in pairs) / n
    mean_y = sum(p[1] for p in pairs) / n
    denominator = sum((p[0] - mean_x) ** 2 for p in pairs)
    if denominator == 0:
        return None
    slope = sum((p[0] - mean_x) * (p[1] - mean_y) for p in pairs) / denominator
    return round(slope * 10, 2)


async def _fetch_archive(
    client: httpx.AsyncClient, loc: dict, start: date, end: date, system: dict
) -> dict:
    resp = await client.get(
        ARCHIVE_URL,
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(DAILY_FIELDS),
            "timezone": "auto",
            **system["api"],
        },
    )
    resp.raise_for_status()
    return resp.json()["daily"]


async def get_historical_weather(
    client: httpx.AsyncClient,
    location: str,
    start_date: str,
    end_date: str,
    units: str = "metric",
) -> dict:
    """Observed weather for a past date range, with a summary of the period."""
    system = unit_system(units)
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")

    if end < start:
        raise ValueError("end_date must be on or after start_date")
    if start < ARCHIVE_START:
        raise ValueError(f"The archive starts on {ARCHIVE_START.isoformat()}")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(
            f"Range is too long. Ask for at most {MAX_RANGE_DAYS} days, "
            "or use get_climate_trend for multi-year questions."
        )

    loc = await geocode(client, location)
    daily = await _fetch_archive(client, loc, start, end, system)

    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_sum") or []
    codes = daily.get("weather_code") or []

    rows = [
        {
            "date": d,
            "condition": describe(codes[i] if i < len(codes) else None),
            "temp_max": highs[i] if i < len(highs) else None,
            "temp_min": lows[i] if i < len(lows) else None,
            "precipitation": rain[i] if i < len(rain) else None,
        }
        for i, d in enumerate(dates)
    ]

    summary = {
        "days_covered": len(dates),
        "mean_temp_max": _mean(highs),
        "mean_temp_min": _mean(lows),
        "hottest_day": _extreme(highs, dates, max),
        "coldest_day": _extreme(lows, dates, min),
        "total_precipitation": _total(rain),
        "wettest_day": _extreme(rain, dates, max),
        "rain_days": sum(1 for v in rain if v is not None and v >= RAIN_DAY_MM),
        "rain_day_threshold": RAIN_DAY_MM,
    }

    result = {
        "location": location_summary(loc),
        "units": system["labels"],
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": summary,
    }

    # Long ranges would flood the model's context with rows it can't use.
    if len(rows) <= MAX_DAILY_ROWS:
        result["days"] = rows
    else:
        result["days"] = []
        result["note"] = (
            f"{len(rows)} days in range; per-day rows omitted. "
            "The summary covers the whole period."
        )
    return result


async def get_climate_trend(
    client: httpx.AsyncClient,
    location: str,
    month: int,
    start_year: int,
    end_year: int,
    units: str = "metric",
) -> dict:
    """How one calendar month has changed across years at one place."""
    system = unit_system(units)
    month = int(month)
    start_year, end_year = int(start_year), int(end_year)

    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if end_year < start_year:
        raise ValueError("end_year must be on or after start_year")
    if end_year - start_year + 1 > MAX_TREND_YEARS:
        raise ValueError(f"Ask for at most {MAX_TREND_YEARS} years at a time")
    if start_year < ARCHIVE_START.year:
        raise ValueError(f"The archive starts in {ARCHIVE_START.year}")

    loc = await geocode(client, location)
    daily = await _fetch_archive(
        client,
        loc,
        date(start_year, 1, 1),
        min(date(end_year, 12, 31), date.today()),
        system,
    )

    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_sum") or []

    buckets: dict[int, dict[str, list]] = {}
    for i, iso in enumerate(dates):
        year, month_part = int(iso[:4]), int(iso[5:7])
        if month_part != month:
            continue
        bucket = buckets.setdefault(year, {"high": [], "low": [], "rain": []})
        bucket["high"].append(highs[i] if i < len(highs) else None)
        bucket["low"].append(lows[i] if i < len(lows) else None)
        bucket["rain"].append(rain[i] if i < len(rain) else None)

    years = sorted(buckets)
    rows = [
        {
            "year": year,
            "mean_temp_max": _mean(buckets[year]["high"]),
            "mean_temp_min": _mean(buckets[year]["low"]),
            "total_precipitation": _total(buckets[year]["rain"]),
            "days_with_data": len(buckets[year]["high"]),
        }
        for year in years
    ]

    month_name = date(2000, month, 1).strftime("%B")
    return {
        "location": location_summary(loc),
        "units": system["labels"],
        "month": month,
        "month_name": month_name,
        "years": [years[0], years[-1]] if years else [],
        "by_year": rows,
        "trend": {
            "mean_temp_max_per_decade": _trend_per_decade(
                years, [r["mean_temp_max"] for r in rows]
            ),
            "mean_temp_min_per_decade": _trend_per_decade(
                years, [r["mean_temp_min"] for r in rows]
            ),
            "precipitation_per_decade": _trend_per_decade(
                years, [r["total_precipitation"] for r in rows]
            ),
            "method": (
                "Least-squares slope across yearly means, scaled to change per "
                "decade. Positive means increasing."
            ),
        },
    }
