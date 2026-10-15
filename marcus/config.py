import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    rubika_bot_token: str
    openrouter_api_key: str
    openrouter_model: str
    database_path: str
    max_history_messages: int
    bot_name: str
    proactive_replies: bool
    proactive_probability: float
    reply_cooldown_seconds: int

def load_settings() -> Settings:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    rubika_token = os.getenv("RUBIKA_BOT_TOKEN", "").strip()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not telegram_token and not rubika_token:
        raise RuntimeError("حداقل یکی از TELEGRAM_BOT_TOKEN یا RUBIKA_BOT_TOKEN را در .env تنظیم کن.")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY در فایل .env تنظیم نشده است.")
    try:
        history_limit = max(2, min(40, int(os.getenv("MAX_HISTORY_MESSAGES", "12"))))
    except ValueError:
        history_limit = 12
    try:
        proactive_probability = max(0.0, min(0.12, float(os.getenv("PROACTIVE_PROBABILITY", "0.025"))))
    except ValueError:
        proactive_probability = 0.025
    try:
        cooldown = max(30, min(3600, int(os.getenv("REPLY_COOLDOWN_SECONDS", "180"))))
    except ValueError:
        cooldown = 180
    return Settings(
        telegram_bot_token=telegram_token,
        rubika_bot_token=rubika_token,
        openrouter_api_key=api_key,
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini",
        database_path=os.getenv("DATABASE_PATH", "marcus.sqlite3").strip() or "marcus.sqlite3",
        max_history_messages=history_limit,
        bot_name=os.getenv("BOT_NAME", "مارکوس").strip() or "مارکوس",
        proactive_replies=os.getenv("PROACTIVE_REPLIES", "false").strip().lower() in {"1", "true", "yes", "on"},
        proactive_probability=proactive_probability,
        reply_cooldown_seconds=cooldown,
    )
