import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import FakeLLM, llm_response, severe_handler, text_block, tool_block


@pytest.fixture
def client():
    """A running app whose weather calls hit the severe-weather mock."""
    with TestClient(app) as test_client:
        app.state.http = httpx.AsyncClient(
            transport=httpx.MockTransport(severe_handler)
        )
        app.state.scheduler.http = app.state.http
        app.state.db.execute("DELETE FROM alerts")
        app.state.db.execute("DELETE FROM locations")
        app.state.db.commit()
        yield test_client


def test_health_reports_llm_and_scheduler_state(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm_configured"] is False
    assert body["alerts"]["running"] is False


def test_tools_endpoint_lists_every_tool(client):
    names = [t["name"] for t in client.get("/api/tools").json()["tools"]]
    assert names == [
        "get_current_weather",
        "get_forecast",
        "get_weather_alerts",
        "get_historical_weather",
        "get_climate_trend",
    ]


def test_languages_endpoint(client):
    body = client.get("/api/languages").json()
    codes = [lang["code"] for lang in body["languages"]]
    assert "hi" in codes and "te" in codes
    assert body["default"] == "en"
    assert all(lang["speech_tag"] for lang in body["languages"])


def test_forecast_route(client):
    body = client.get("/api/weather/forecast", params={"location": "Paris"}).json()
    assert body["location"]["name"] == "Paris"
    assert len(body["days"]) == 3


def test_unknown_location_is_a_404(client):
    response = client.get("/api/weather/current", params={"location": "Nowhereville"})
    assert response.status_code == 404
    assert "No location found" in response.json()["detail"]


def test_bad_date_is_a_422(client):
    response = client.get(
        "/api/weather/history",
        params={"location": "Paris", "start_date": "nope", "end_date": "2023-06-02"},
    )
    assert response.status_code == 422
    assert "YYYY-MM-DD" in response.json()["detail"]


def test_chat_without_a_key_is_a_503(client):
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503


def test_chat_returns_a_reply_and_a_trace(client):
    app.state.llm = FakeLLM(
        [
            llm_response(
                [
                    text_block("Using get_forecast because you asked about tomorrow."),
                    tool_block("t1", "get_forecast", {"location": "Paris", "days": 2}),
                ],
                "tool_use",
            ),
            llm_response([text_block("Rain tomorrow in Paris.")], "end_turn"),
        ]
    )

    body = client.post(
        "/api/chat", json={"message": "Paris tomorrow?", "language": "hi"}
    ).json()

    assert body["reply"] == "Rain tomorrow in Paris."
    assert body["trace"]["language"] == "hi"
    assert body["trace"]["steps"][0]["tool_calls"][0]["tool"] == "get_forecast"
    app.state.llm = None


def test_saving_a_location_resolves_it_and_checks_alerts(client):
    created = client.post("/api/locations", json={"location": "Paris, France"})
    assert created.status_code == 201
    assert created.json()["country"] == "France"

    alerts = client.get("/api/alerts", params={"language": "en"}).json()["alerts"]
    assert alerts, "saving a location should populate alerts straight away"
    assert alerts[0]["headline"]


def test_saving_the_same_place_twice_is_a_409(client):
    client.post("/api/locations", json={"location": "Paris, France"})
    duplicate = client.post("/api/locations", json={"location": "Paris, France"})
    assert duplicate.status_code == 409


def test_acknowledging_an_alert(client):
    client.post("/api/locations", json={"location": "Paris, France"})
    alert_id = client.get("/api/alerts").json()["alerts"][0]["id"]

    assert client.post(f"/api/alerts/{alert_id}/ack").status_code == 204

    unread = client.get("/api/alerts", params={"unacknowledged_only": True}).json()
    assert alert_id not in [a["id"] for a in unread["alerts"]]


def test_refresh_runs_a_scheduler_pass(client):
    client.post("/api/locations", json={"location": "Paris, France"})
    body = client.post("/api/alerts/refresh").json()
    assert body["locations_checked"] == 1
    assert body["ran_at"]


def test_deleting_a_location(client):
    location_id = client.post(
        "/api/locations", json={"location": "Paris, France"}
    ).json()["id"]

    assert client.delete(f"/api/locations/{location_id}").status_code == 204
    assert client.get("/api/locations").json()["locations"] == []


def test_one_off_alert_check_saves_nothing(client):
    body = client.get(
        "/api/alerts/check", params={"location": "Paris", "days": 3, "language": "te"}
    ).json()
    assert body["alerts"][0]["language"] == "te"
    assert client.get("/api/locations").json()["locations"] == []
