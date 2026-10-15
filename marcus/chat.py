import asyncio
import logging

from .ai import EMPTY_RESPONSE, ERROR_RESPONSE, OpenRouterClient, is_failure_reply
from .db import Database

logger = logging.getLogger(__name__)


class ChatLocks:
    """برای هر چت یک قفل؛ پیام‌های یک چت پشت‌سرهم پردازش می‌شن و جواب‌ها قاطی نمی‌شن."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def get(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks[key] = asyncio.Lock()
        return lock


async def generate_reply(
    db: Database,
    ai: OpenRouterClient,
    *,
    platform: str,
    chat_id: str,
    user_id: str,
    text: str,
    memories: list[str],
    history_limit: int,
) -> str:
    """پیام کاربر رو ذخیره می‌کنه، جواب می‌گیره و فقط جواب سالم رو تو تاریخچه نگه می‌داره.

    اگر جواب خطا بود (لیمیت، خالی، ...) هم جواب خطا و هم پیام کاربر از تاریخچه پاک می‌شن
    تا پیام‌های بعدی به پیام بی‌جواب نچسبن و مدل خطا رو تقلید نکنه.
    """
    message_id = db.add_message(platform, chat_id, user_id, "user", text)
    history = db.history(platform, chat_id, history_limit)
    try:
        answer = await ai.reply(history, memories)
    except Exception:
        logger.exception("AI request failed (%s)", platform)
        answer = ERROR_RESPONSE
    if not isinstance(answer, str) or answer.strip().casefold() in {"", "none", "null"}:
        answer = EMPTY_RESPONSE
    answer = answer.strip()
    if is_failure_reply(answer):
        db.delete_message(message_id)
    else:
        db.add_message(platform, chat_id, user_id, "assistant", answer)
    return answer
