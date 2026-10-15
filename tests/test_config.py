import os
import unittest
from unittest.mock import patch

from marcus.config import load_settings


class SettingsTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "telegram-test-token",
            "RUBIKA_BOT_TOKEN": "",
            "OPENROUTER_API_KEY": "openrouter-test-key",
        },
        clear=True,
    )
    def test_free_auto_router_is_default_model(self):
        settings = load_settings()
        self.assertEqual(settings.openrouter_model, "openrouter/free")

    @patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "telegram-test-token",
            "RUBIKA_BOT_TOKEN": "",
            "OPENROUTER_API_KEY": "openrouter-test-key",
            "OPENROUTER_MODEL": "custom/model",
            "MAX_HISTORY_MESSAGES": "500",
            "PROACTIVE_PROBABILITY": "2",
            "REPLY_COOLDOWN_SECONDS": "1",
        },
        clear=True,
    )
    def test_settings_are_clamped_to_safe_ranges(self):
        settings = load_settings()
        self.assertEqual(settings.openrouter_model, "custom/model")
        self.assertEqual(settings.max_history_messages, 40)
        self.assertEqual(settings.proactive_probability, 0.12)
        self.assertEqual(settings.reply_cooldown_seconds, 30)


if __name__ == "__main__":
    unittest.main()
