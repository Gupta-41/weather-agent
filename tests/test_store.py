import pytest

from backend import store
from backend.alerts.scheduler import AlertScheduler

PARIS = {
    "name": "Paris",
    "region": "Île-de-France",
    "country": "France",
    "latitude": 48.85,
    "longitude": 2.35,
    "timezone": "Europe/Paris",
}

ALERT = {
    "code": "very_heavy_rain",
    "severity": "watch",
    "date": "2026-09-20",
    "value": 130.0,
    "unit": "mm",
    "metric": "precipitation_sum",
    "location": "Paris",
}


async def save_paris(conn, **kwargs):
    return await store.add_location(conn, label="Paris, France", place=PARIS, **kwargs)


async def test_add_and_list_locations(conn):
    saved = await save_paris(conn, language="hi")
    assert saved["name"] == "Paris" and saved["language"] == "hi"
    assert [row["id"] for row in await store.list_locations(conn)] == [saved["id"]]


async def test_same_coordinates_cannot_be_saved_twice(conn):
    await save_paris(conn)
    with pytest.raises(store.DuplicateLocation):
        await save_paris(conn)


async def test_delete_location(conn):
    saved = await save_paris(conn)
    await store.delete_location(conn, saved["id"])
    assert await store.list_locations(conn) == []


async def test_deleting_a_missing_location_raises(conn):
    with pytest.raises(store.LocationMissing):
        await store.delete_location(conn, 999)


async def test_alerts_are_deduplicated_by_fingerprint(conn):
    saved = await save_paris(conn)
    assert await store.save_alerts(conn, saved["id"], [ALERT]) == 1
    assert await store.save_alerts(conn, saved["id"], [ALERT]) == 0
    assert len(await store.list_alerts(conn)) == 1


async def test_an_upgraded_severity_is_a_new_alert(conn):
    saved = await save_paris(conn)
    await store.save_alerts(conn, saved["id"], [ALERT])
    upgraded = {**ALERT, "severity": "warning"}
    assert await store.save_alerts(conn, saved["id"], [upgraded]) == 1


async def test_alerts_are_rendered_in_the_requested_language(conn):
    saved = await save_paris(conn)
    await store.save_alerts(conn, saved["id"], [ALERT])

    english = (await store.list_alerts(conn, language="en"))[0]
    telugu = (await store.list_alerts(conn, language="te"))[0]

    assert english["headline"] != telugu["headline"]
    assert english["location_label"] == "Paris, France"


async def test_acknowledging_removes_an_alert_from_the_unread_list(conn):
    saved = await save_paris(conn)
    await store.save_alerts(conn, saved["id"], [ALERT])
    alert = (await store.list_alerts(conn))[0]

    await store.acknowledge_alert(conn, alert["id"])

    assert await store.list_alerts(conn, unacknowledged_only=True) == []
    assert (await store.list_alerts(conn))[0]["acknowledged"] is True


async def test_deleting_a_location_removes_its_alerts(conn):
    saved = await save_paris(conn)
    await store.save_alerts(conn, saved["id"], [ALERT])
    await store.delete_location(conn, saved["id"])
    assert await store.list_alerts(conn) == []


# --- scheduler -------------------------------------------------------------


async def test_scheduler_stores_alerts_for_saved_locations(conn, severe_http):
    await save_paris(conn)
    scheduler = AlertScheduler(conn, severe_http, lookahead_days=3)

    result = await scheduler.run_once()

    assert result["locations_checked"] == 1
    assert result["new_alerts"] > 0
    assert result["failures"] == []
    assert len(await store.list_alerts(conn)) == result["new_alerts"]


async def test_second_pass_adds_nothing_new(conn, severe_http):
    await save_paris(conn)
    scheduler = AlertScheduler(conn, severe_http, lookahead_days=3)
    await scheduler.run_once()
    assert (await scheduler.run_once())["new_alerts"] == 0


async def test_one_bad_location_does_not_stop_the_pass(conn, severe_http):
    await save_paris(conn)
    await store.add_location(
        conn,
        label="Nowhereville",
        place={**PARIS, "name": "Nowhereville", "latitude": 0.0, "longitude": 0.0},
    )
    scheduler = AlertScheduler(conn, severe_http, lookahead_days=3)

    result = await scheduler.run_once()

    assert result["locations_checked"] == 1
    assert len(result["failures"]) == 1
    assert scheduler.last_error


async def test_status_reports_configuration(conn, severe_http):
    scheduler = AlertScheduler(conn, severe_http, interval_minutes=15, lookahead_days=4)
    status = scheduler.status()
    assert status["running"] is False
    assert status["interval_minutes"] == 15
    assert status["lookahead_days"] == 4
