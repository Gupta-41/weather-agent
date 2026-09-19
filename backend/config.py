import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "6"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/weather.db")

# Background alert polling for saved locations.
ALERTS_ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() not in {"0", "false", "no"}
ALERT_POLL_MINUTES = int(os.getenv("ALERT_POLL_MINUTES", "30"))
ALERT_LOOKAHEAD_DAYS = int(os.getenv("ALERT_LOOKAHEAD_DAYS", "5"))

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
