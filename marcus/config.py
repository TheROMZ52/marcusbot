import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openrouter_api_key: str
    openrouter_model: str
    database_path: str
    max_history_messages: int
    bot_name: str

def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN در فایل .env تنظیم نشده است.")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY در فایل .env تنظیم نشده است.")
    try:
        history_limit = max(2, min(40, int(os.getenv("MAX_HISTORY_MESSAGES", "12"))))
    except ValueError:
        history_limit = 12
    return Settings(
        telegram_bot_token=token,
        openrouter_api_key=api_key,
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip(),
        database_path=os.getenv("DATABASE_PATH", "marcus.sqlite3").strip(),
        max_history_messages=history_limit,
        bot_name=os.getenv("BOT_NAME", "مارکوس").strip() or "مارکوس",
    )
