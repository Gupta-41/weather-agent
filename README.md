# WeatherGPT

A conversational weather and local-alert assistant built on Claude's tool use.
Ask a question in plain language, in any of seven Indian languages, and the
agent decides which data source to reach for — current conditions, a forecast,
a severe-weather check, the historical archive, or a multi-year climate trend —
then returns a **Tool Selection Trace** showing every decision it made.

Built for problem statement **A2** of the Capabl Agentic AI Saksham National
Level Agentic AI Hackathon.

Weather data comes from [Open-Meteo](https://open-meteo.com), which needs no API
key. The LLM is Claude via the Anthropic API.

## Run it

Two terminals. Backend:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env        # then put your ANTHROPIC_API_KEY in .env
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env        # defaults to http://localhost:8000
npm run dev
```

Open http://localhost:5173. Interactive API docs at http://localhost:8000/docs.

```bash
pytest                      # 74 tests, mocked weather and LLM, no network or key needed
```

Everything except `/api/chat` works without an Anthropic key, including alerts —
useful when you're debugging tool output and don't want to burn tokens.

## What it does

| Step | Feature |
| --- | --- |
| 1–3 | FastAPI backend over Open-Meteo |
| 4–5 | Current-conditions and forecast tools |
| 6 | Claude agent with tool calling |
| 7 | **Tool Selection Trace** (compulsory add-on) |
| 8 | React UI |
| 9 | Severe-weather alerts, checked in the background |
| 10 | Saved locations in SQLite |
| 11 | Seven Indian languages |
| 12 | Voice in and voice out |
| 13 | Historical weather and climate trends |
| 14 | Render + Vercel deployment — see [DEPLOY.md](DEPLOY.md) |

## Tool Selection Trace

`POST /api/chat` returns a `trace` alongside the reply, with one step per model
call:

```json
{
  "model": "claude-sonnet-5",
  "language": "hi",
  "total_ms": 2140,
  "steps": [
    {
      "step": 1,
      "available_tools": ["get_current_weather", "get_forecast", "get_weather_alerts",
                          "get_historical_weather", "get_climate_trend"],
      "model_text": "I'll use get_forecast because you asked about tomorrow.",
      "decision": "use_tools",
      "stop_reason": "tool_use",
      "tool_calls": [
        {"tool": "get_forecast", "input": {"location": "Hyderabad", "days": 2},
         "ok": true, "duration_ms": 412, "result_preview": "{...}", "error": null}
      ],
      "model_latency_ms": 1180,
      "input_tokens": 640,
      "output_tokens": 55
    },
    {"step": 2, "decision": "final_answer", "tool_calls": []}
  ]
}
```

`model_text` is the one-sentence explanation the system prompt asks Claude to
give *before* choosing a tool, so it reflects the model's actual reasoning
rather than a justification written after the fact.

In the UI the trace sits under each reply. Collapsed it reads as a tape — one
marker per model call, the tools it picked, total latency. Expanded, each step
shows the full candidate tool list, the reason given, the exact arguments
passed, and what came back.

## The five tools

| Tool | For |
| --- | --- |
| `get_current_weather` | Conditions right now |
| `get_forecast` | Today through 16 days out |
| `get_weather_alerts` | Whether a severe-weather threshold is crossed |
| `get_historical_weather` | What the weather actually was, over a past range |
| `get_climate_trend` | How one month has shifted across many years |

Tool descriptions are written to be *discriminative* — each says what it is for
**and** what to reach for instead. Tool-selection quality is the evaluation
criterion for this problem, and the description is where that quality is
decided, not the agent loop.

## Alerts

Thresholds follow India Meteorological Department practice where a public number
exists. The 24-hour rainfall bands are IMD's; 62 km/h is IMD's gale threshold.
Heat and cold use absolute values rather than IMD's departure-from-normal
method, because departure needs a climatological normal we don't fetch.

| Band | Advisory | Watch | Warning |
| --- | --- | --- | --- |
| Rain (mm/24h) | ≥ 64.5 | ≥ 115.6 | ≥ 204.5 |
| Heat (°C max) | ≥ 40 | — | ≥ 45 |
| Cold (°C min) | ≤ 10 | ≤ 4 | — |
| Wind (km/h) | ≥ 50 | ≥ 62 | ≥ 88 |
| Storm | — | thunderstorm | hail |

Alert text comes from translated templates, not the LLM. A severe weather
warning should say exactly the same thing every time it fires, and it should
still render when the Anthropic API is down — neither is true of a generated
sentence.

A background task polls every saved location every 30 minutes and stores
anything new, deduplicated by fingerprint. An upgrade from watch to warning on
the same day counts as a new alert, because it is one.

## API

| Endpoint | What it does |
| --- | --- |
| `GET /api/health` | Liveness, whether a key is configured, scheduler state |
| `GET /api/tools` | The tool definitions the agent chooses from |
| `GET /api/languages` | Supported languages with their speech tags |
| `GET /api/weather/current` | Current conditions, no LLM |
| `GET /api/weather/forecast` | Daily forecast, no LLM |
| `GET /api/weather/history` | Past date range with a period summary |
| `GET /api/weather/climate` | Per-year month comparison and trend |
| `GET POST /api/locations` | List and save locations |
| `DELETE /api/locations/{id}` | Remove one |
| `GET /api/alerts` | Stored alerts, rendered in a language |
| `POST /api/alerts/refresh` | Force a scheduler pass |
| `POST /api/alerts/{id}/ack` | Dismiss one |
| `GET /api/alerts/check` | One-off check that saves nothing |
| `POST /api/chat` | `{message, history, language}` → `{reply, trace}` |

The chat endpoint is stateless: the client sends prior turns in `history`.

## Languages

English, Hindi, Telugu, Tamil, Bengali, Marathi, Kannada.

Three layers, deliberately different:

- **Agent replies** — Claude answers in the requested language.
- **Alert text** — translated templates (en/hi/te), English fallback.
- **Interface labels** — a static table, so the UI reads correctly even offline.

The agent's tool-choice sentence stays in English on purpose. It's instrumentation
for the trace panel, not something the user reads.

## Voice

Browser Web Speech API — recognition for input, synthesis for reading replies
aloud. Nothing is uploaded and no key is needed. Support is uneven, so the
microphone only appears where the browser actually supports it.

**Use Chrome.** Firefox has no speech recognition, and Safari's Indian-language
coverage is patchy.

## Adding a tool

Write an async function in `backend/tools/`, add its definition to
`TOOL_DEFINITIONS` and its function to `_TOOLS` in `backend/tools/registry.py`.
The agent, the trace and the UI pick it up with no other changes.

## Layout

```
backend/
  main.py            FastAPI app and routes
  config.py          Settings from environment
  db.py              SQLite schema and connection
  store.py           Saved locations and alert persistence
  languages.py       Supported languages and normalization
  units.py           metric / imperial mapping
  weather_codes.py   WMO code → description
  tools/             geocode, current, forecast, alerts, history, registry
  alerts/            threshold rules, localized messages, background scheduler
  agent/             agent loop and trace
frontend/
  src/App.jsx        State and data loading
  src/api.js         Backend client
  src/i18n.js        Interface strings
  src/hooks/         Web Speech
  src/components/    TraceTape, Message, Composer, AlertsPanel, SavedLocations
tests/               74 tests, network and LLM mocked
```

## Known limits

- The historical archive lags real time by about five days. The agent is told
  to use the forecast tool for today, yesterday and the day before.
- Climate trends are a least-squares fit over yearly means. Useful for
  direction, not a substitute for a proper climatological analysis.
- Alerts are threshold rules over a forecast, not an official warning product.
  They are not a replacement for IMD bulletins.
- Geocoding picks the first match when a place name is ambiguous. Add a region
  or country — `Hyderabad, India` — to disambiguate.
