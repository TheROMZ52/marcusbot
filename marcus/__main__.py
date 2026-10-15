import logging
from .ai import OpenRouterClient
from .config import load_settings
from .db import Database
from .telegram_adapter import TelegramAdapter

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    db = Database(settings.database_path)
    ai = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model, settings.bot_name)
    app = TelegramAdapter(settings, db, ai).build()
    logging.getLogger(__name__).info("Marcus is starting")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
