import pytest

from backend.tools.history import (
    _trend_per_decade,
    get_climate_trend,
    get_historical_weather,
)


async def test_historical_summary(http):
    data = await get_historical_weather(http, "Paris", "2023-06-01", "2023-06-03")
    summary = data["summary"]
    assert summary["days_covered"] == 9  # whatever the mock returns
    assert summary["hottest_day"]["value"] == 37.0
    assert summary["coldest_day"]["value"] == 23.0
    assert summary["total_precipitation"] == 30.0
    assert summary["rain_days"] == 3
    assert data["period"] == {"start": "2023-06-01", "end": "2023-06-03"}


async def test_historical_includes_rows_for_short_ranges(http):
    data = await get_historical_weather(http, "Paris", "2023-06-01", "2023-06-03")
    assert len(data["days"]) == 9
    assert data["days"][1]["condition"] == "Slight rain"


async def test_historical_rejects_reversed_range(http):
    with pytest.raises(ValueError, match="on or after"):
        await get_historical_weather(http, "Paris", "2023-06-10", "2023-06-01")


async def test_historical_rejects_bad_date_format(http):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        await get_historical_weather(http, "Paris", "June 2023", "2023-06-01")


async def test_historical_rejects_pre_archive_dates(http):
    with pytest.raises(ValueError, match="archive starts"):
        await get_historical_weather(http, "Paris", "1901-01-01", "1901-02-01")


async def test_historical_rejects_ranges_that_belong_in_a_trend(http):
    with pytest.raises(ValueError, match="too long"):
        await get_historical_weather(http, "Paris", "2000-01-01", "2010-01-01")


async def test_climate_trend_buckets_by_year(http):
    data = await get_climate_trend(http, "Paris", month=6, start_year=2023, end_year=2025)
    assert [r["year"] for r in data["by_year"]] == [2023, 2024, 2025]
    assert data["month_name"] == "June"
    assert data["by_year"][0]["mean_temp_max"] == 33.0
    assert data["by_year"][2]["mean_temp_max"] == 35.0


async def test_climate_trend_reports_warming_and_drying(http):
    data = await get_climate_trend(http, "Paris", month=6, start_year=2023, end_year=2025)
    assert data["trend"]["mean_temp_max_per_decade"] == 10.0  # +1°C/yr in the fixture
    assert data["trend"]["precipitation_per_decade"] < 0


async def test_climate_trend_validates_month_and_years(http):
    with pytest.raises(ValueError, match="month must be"):
        await get_climate_trend(http, "Paris", month=13, start_year=2020, end_year=2021)
    with pytest.raises(ValueError, match="on or after"):
        await get_climate_trend(http, "Paris", month=6, start_year=2021, end_year=2020)
    with pytest.raises(ValueError, match="at most"):
        await get_climate_trend(http, "Paris", month=6, start_year=1950, end_year=2025)


def test_trend_needs_at_least_three_points():
    assert _trend_per_decade([2020, 2021], [10.0, 11.0]) is None


def test_trend_ignores_missing_years():
    years = [2020, 2021, 2022, 2023]
    assert _trend_per_decade(years, [10.0, None, 12.0, 13.0]) == 10.0


def test_trend_is_none_when_too_few_years_survive():
    assert _trend_per_decade([2020, 2021, 2022], [10.0, None, 12.0]) is None


def test_flat_series_has_no_trend():
    assert _trend_per_decade([2020, 2021, 2022], [10.0, 10.0, 10.0]) == 0.0
