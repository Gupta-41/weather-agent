import httpx
import pytest

from backend.tools.openmeteo import MAX_RETRIES, get_with_retry


def _responder(statuses):
    """Returns a fresh MockTransport handler that yields one status per call,
    then repeats the last one if called more times than statuses provided."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        i = min(calls["n"], len(statuses) - 1)
        calls["n"] += 1
        status = statuses[i]
        if status == 200:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(status, json={"error": "boom"})

    return handler, calls


async def test_succeeds_immediately_on_200(monkeypatch):
    handler, calls = _responder([200])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp = await get_with_retry(client, "https://example.test/x", {})
    assert resp.status_code == 200
    assert calls["n"] == 1


async def test_retries_once_on_429_then_succeeds(monkeypatch):
    import backend.tools.openmeteo as mod
    monkeypatch.setattr(mod, "RETRY_BASE_DELAY", 0)

    handler, calls = _responder([429, 200])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp = await get_with_retry(client, "https://example.test/x", {})
    assert resp.status_code == 200
    assert calls["n"] == 2


async def test_retries_on_503_then_succeeds(monkeypatch):
    import backend.tools.openmeteo as mod
    monkeypatch.setattr(mod, "RETRY_BASE_DELAY", 0)

    handler, calls = _responder([503, 503, 200])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp = await get_with_retry(client, "https://example.test/x", {})
    assert resp.status_code == 200
    assert calls["n"] == 3  # two failures + the success, within MAX_RETRIES=2


async def test_gives_up_after_max_retries_and_raises(monkeypatch):
    import backend.tools.openmeteo as mod
    monkeypatch.setattr(mod, "RETRY_BASE_DELAY", 0)

    handler, calls = _responder([503, 503, 503, 503])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await get_with_retry(client, "https://example.test/x", {})
    assert calls["n"] == MAX_RETRIES + 1


async def test_non_retryable_status_fails_immediately(monkeypatch):
    import backend.tools.openmeteo as mod
    monkeypatch.setattr(mod, "RETRY_BASE_DELAY", 0)

    handler, calls = _responder([404, 200])  # would succeed if it retried — it must not
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await get_with_retry(client, "https://example.test/x", {})
    assert calls["n"] == 1


async def test_network_failure_is_retried(monkeypatch):
    import backend.tools.openmeteo as mod
    monkeypatch.setattr(mod, "RETRY_BASE_DELAY", 0)

    attempts = {"n": 0}

    def handler(request: httpx.Request):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp = await get_with_retry(client, "https://example.test/x", {})
    assert resp.status_code == 200
    assert attempts["n"] == 2
