import io
import logging
import unittest

from marcus.log_safety import MASK, RedactingFormatter, setup_logging

TG = "123456789:AAH_fake-token_abcdefghijklmnopqrstuvwxyz1"


def capture(formatter, message, *args, exc=False):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger = logging.getLogger("test.log_safety")
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    if exc:
        try:
            raise RuntimeError(message % args)
        except RuntimeError:
            logger.exception("failed")
    else:
        logger.info(message, *args)
    return stream.getvalue()


class RedactionTests(unittest.TestCase):
    def test_telegram_token_in_url_is_masked_without_knowing_it(self):
        out = capture(RedactingFormatter("%(message)s"), "HTTP Request: POST https://api.telegram.org/bot%s/getUpdates", TG)
        self.assertNotIn(TG, out)
        self.assertIn(MASK, out)

    def test_configured_secrets_and_multiple_keys_are_masked(self):
        fmt = RedactingFormatter("%(message)s")
        fmt.add_secrets("rubika-secret-token-value", "key-one-abcdef,key-two-abcdef")
        out = capture(fmt, "a rubika-secret-token-value b key-one-abcdef c key-two-abcdef")
        for secret in ("rubika-secret-token-value", "key-one-abcdef", "key-two-abcdef"):
            self.assertNotIn(secret, out)

    def test_bearer_and_openrouter_keys_are_masked(self):
        out = capture(RedactingFormatter("%(message)s"), "Authorization: Bearer sk-or-v1-abcdef1234567890abcdef")
        self.assertNotIn("abcdef1234567890", out)
        self.assertIn("Bearer", out)

    def test_traceback_is_masked_too(self):
        out = capture(RedactingFormatter("%(message)s"), "boom %s", TG, exc=True)
        self.assertNotIn(TG, out)
        self.assertIn("Traceback", out)

    def test_normal_text_is_untouched(self):
        out = capture(RedactingFormatter("%(message)s"), "سلام ساعت 12:30 شد")
        self.assertIn("سلام ساعت 12:30 شد", out)

    def test_httpx_request_logging_is_silenced(self):
        setup_logging()
        self.assertGreaterEqual(logging.getLogger("httpx").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
