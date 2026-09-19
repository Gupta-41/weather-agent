from contextlib import asynccontextmanager
from typing import Literal

import anthropic
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend import config, db, store
from backend.agent.agent import run_agent
from backend.alerts.scheduler import AlertScheduler
from backend.languages import as_list, normalize
from backend.tools.alerts import get_weather_alerts
from backend.tools.current import get_current_weather
from backend.tools.forecast import get_forecast
from backend.tools.geocode import LocationNotFound, geocode
from backend.tools.history import get_climate_trend, get_historical_weather
from backend.tools.openmeteo import location_summary
from backend.tools.registry import TOOL_DEFINITIONS

Units = Literal["metric", "imperial"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=15.0)
    app.state.llm = (
        anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        if config.ANTHROPIC_API_KEY
        else None
    )
    app.state.db = db.connect()
    db.init(app.state.db)

    app.state.scheduler = AlertScheduler(app.state.db, app.state.http)
    if config.ALERTS_ENABLED:
        app.state.scheduler.start()

    yield

    await app.state.scheduler.stop()
    await app.state.http.aclose()
    app.state.db.close()


app = FastAPI(title="WeatherGPT Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LocationNotFound)
async def location_not_found(_: Request, exc: LocationNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(store.LocationMissing)
async def saved_location_missing(_: Request, exc: store.LocationMissing):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(store.DuplicateLocation)
async def duplicate_location(_: Request, exc: store.DuplicateLocation):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(httpx.HTTPError)
async def upstream_weather_error(_: Request, exc: httpx.HTTPError):
    return JSONResponse(
        status_code=502, content={"detail": "Weather provider request failed"}
    )


@app.exception_handler(anthropic.APIError)
async def upstream_llm_error(_: Request, exc: anthropic.APIError):
    return JSONResponse(status_code=502, content={"detail": "LLM request failed"})


@app.exception_handler(ValueError)
async def bad_value(_: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# --- meta ------------------------------------------------------------------


@app.get("/api/health")
async def health(request: Request):
    return {
        "status": "ok",
        "llm_configured": request.app.state.llm is not None,
        "alerts": request.app.state.scheduler.status(),
    }


@app.get("/api/tools")
async def tools():
    return {"tools": TOOL_DEFINITIONS}


@app.get("/api/languages")
async def languages():
    return {"languages": as_list(), "default": normalize(config.DEFAULT_LANGUAGE)}


# --- direct weather (no LLM) ----------------------------------------------


@app.get("/api/weather/current")
async def current(
    request: Request,
    location: str = Query(..., min_length=1, max_length=100),
    units: Units = "metric",
):
    return await get_current_weather(request.app.state.http, location, units)


@app.get("/api/weather/forecast")
async def forecast(
    request: Request,
    location: str = Query(..., min_length=1, max_length=100),
    days: int = Query(5, ge=1, le=16),
    units: Units = "metric",
):
    return await get_forecast(request.app.state.http, location, days, units)


@app.get("/api/weather/history")
async def history(
    request: Request,
    location: str = Query(..., min_length=1, max_length=100),
    start_date: str = Query(...),
    end_date: str = Query(...),
    units: Units = "metric",
):
    return await get_historical_weather(
        request.app.state.http, location, start_date, end_date, units
    )


@app.get("/api/weather/climate")
async def climate(
    request: Request,
    location: str = Query(..., min_length=1, max_length=100),
    month: int = Query(..., ge=1, le=12),
    start_year: int = Query(..., ge=1940),
    end_year: int = Query(..., ge=1940),
    units: Units = "metric",
):
    return await get_climate_trend(
        request.app.state.http, location, month, start_year, end_year, units
    )


# --- saved locations -------------------------------------------------------


class LocationIn(BaseModel):
    location: str = Field(min_length=1, max_length=100)
    units: Units = "metric"
    language: str = "en"


@app.get("/api/locations")
async def locations(request: Request):
    return {"locations": await store.list_locations(request.app.state.db)}


@app.post("/api/locations", status_code=201)
async def save_location(body: LocationIn, request: Request):
    """Resolve the place first, so we store coordinates rather than a string."""
    place = location_summary(await geocode(request.app.state.http, body.location))
    saved = await store.add_location(
        request.app.state.db,
        label=body.location.strip(),
        place=place,
        units=body.units,
        language=normalize(body.language),
    )
    # Check it immediately — a location saved during a demo should not sit
    # empty until the next poll.
    try:
        result = await get_weather_alerts(
            request.app.state.http, body.location, config.ALERT_LOOKAHEAD_DAYS
        )
        await store.save_alerts(request.app.state.db, saved["id"], result["alerts"])
    except Exception:
        pass
    return saved


@app.delete("/api/locations/{location_id}", status_code=204)
async def remove_location(location_id: int, request: Request):
    await store.delete_location(request.app.state.db, location_id)
    return JSONResponse(status_code=204, content=None)


# --- alerts ----------------------------------------------------------------


@app.get("/api/alerts")
async def alerts(
    request: Request,
    language: str = "en",
    unacknowledged_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
):
    return {
        "alerts": await store.list_alerts(
            request.app.state.db,
            language=normalize(language),
            unacknowledged_only=unacknowledged_only,
            limit=limit,
        ),
        "scheduler": request.app.state.scheduler.status(),
    }


@app.post("/api/alerts/refresh")
async def refresh_alerts(request: Request):
    return await request.app.state.scheduler.run_once()


@app.post("/api/alerts/{alert_id}/ack", status_code=204)
async def ack_alert(alert_id: int, request: Request):
    await store.acknowledge_alert(request.app.state.db, alert_id)
    return JSONResponse(status_code=204, content=None)


@app.get("/api/alerts/check")
async def check_location_alerts(
    request: Request,
    location: str = Query(..., min_length=1, max_length=100),
    days: int = Query(5, ge=1, le=16),
    language: str = "en",
):
    """One-off check that doesn't save anything."""
    return await get_weather_alerts(
        request.app.state.http, location, days, normalize(language)
    )


# --- chat ------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    language: str = "en"


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    llm = request.app.state.llm
    if llm is None:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not set")

    result = await run_agent(
        llm=llm,
        http=request.app.state.http,
        message=req.message,
        history=[m.model_dump() for m in req.history],
        language=normalize(req.language),
    )
    return {"reply": result.reply, "trace": result.trace.to_dict()}
