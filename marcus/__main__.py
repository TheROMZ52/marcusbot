import logging
import threading

from .ai import OpenRouterClient
from .config import load_settings
from .db import Database
from .rubika_adapter import RubikaAdapter
from .setup import run_first_setup
from .telegram_adapter import TelegramAdapter


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_first_setup()
    settings = load_settings()
    db = Database(settings.database_path)
    ai = OpenRouterClient(
        settings.openrouter_api_key,
        settings.openrouter_model,
        settings.bot_name,
        fallback_models=settings.openrouter_fallback_models or None,
    )

    if settings.rubika_bot_token:
        rubika = RubikaAdapter(settings, db, ai)
        if settings.telegram_bot_token:
            thread = threading.Thread(target=rubika.run, name="marcus-rubika", daemon=True)
            thread.start()
        else:
            rubika.run()
            return

    if settings.telegram_bot_token:
        app = TelegramAdapter(settings, db, ai).build()
        logging.getLogger(__name__).info("Starting Marcus Telegram adapter")
        app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
