import logging
import re

# الگوهای عمومی: توکن ربات تلگرام، کلید OpenRouter، هدر Bearer، و آدرس /bot<token>/
_PATTERNS = (
    re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{30,}"),
    re.compile(r"\bsk-or-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{10,}"),
)

MASK = "***"


class RedactingFormatter(logging.Formatter):
    """خروجی نهایی لاگ (با traceback) را قبل از چاپ ماسک می‌کند."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._secrets: set[str] = set()

    def add_secrets(self, *values: str) -> None:
        for value in values:
            for part in (value or "").split(","):
                part = part.strip()
                if len(part) >= 8:
                    self._secrets.add(part)

    def redact(self, text: str) -> str:
        for secret in sorted(self._secrets, key=len, reverse=True):
            text = text.replace(secret, MASK)
        for pattern in _PATTERNS:
            if pattern.groups:
                text = pattern.sub(lambda m: m.group(1) + MASK, text)
            else:
                text = pattern.sub(MASK, text)
        return text

    def format(self, record: logging.LogRecord) -> str:
        return self.redact(super().format(record))


def setup_logging() -> RedactingFormatter:
    formatter = RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    # این‌ها هر درخواست HTTP را همراه آدرس کامل (که توکن تلگرام توشه) لاگ می‌کنند.
    for noisy in ("httpx", "httpcore", "telegram.ext.Updater", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return formatter
