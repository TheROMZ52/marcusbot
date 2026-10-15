import logging
import re
from .ai import OpenRouterClient
from .config import Settings
from .db import Database

logger = logging.getLogger(__name__)

def value(obj, *names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        found = getattr(obj, name, None)
        if found is not None:
            return found
    return default

class RubikaAdapter:
    def __init__(self, settings: Settings, db: Database, ai: OpenRouterClient):
        self.settings = settings
        self.db = db
        self.ai = ai

    async def handle(self, client, update):
        message = value(update, "new_message", "updated_message", default=None)
        if message is None:
            return
        text = value(message, "text", default="")
        if not isinstance(text, str) or not text.strip():
            return
        text = text.strip()
        sender = value(message, "sender_id", "author_guid", "user_id", "from_id", default="")
        chat_id = value(update, "chat_id", default="")
        if not sender or not chat_id:
            logger.debug("Ignoring Rubika update without sender/chat id")
            return
        sender = str(sender)
        chat_id = str(chat_id)
        if str(value(message, "sender_type", default="")) == "Bot":
            return
        display = str(value(message, "sender_name", "name", "first_name", default=sender))
        identity_id = self.db.ensure_identity("rubika", sender, display)

        parts = text.split(maxsplit=1)
        command = parts[0].split("@", 1)[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command in {"/start", "/help"}:
            await update.reply(
                "سلام، من مارکوسم. توی گروه با «مارکوس» صدام کن.\n"
                "/remember متن — ثبت خاطره\n/memories — دیدن خاطرات\n"
                "/forget شماره — حذف خاطره\n/linkcode — کد پیوند ۱۰ دقیقه‌ای\n"
                "/link کد — پیوند حساب\n/forgetme — پاک‌کردن خاطرات"
            )
            return
        if command == "/remember":
            if not arg:
                await update.reply("روش استفاده: /remember چیزی که می‌خوای یادم بمونه")
                return
            if re.search(r"(?i)(password|passcode|api[_ -]?key|token|رمز عبور|رمز کارت|کلید api)", arg):
                await update.reply("چیزهایی مثل رمز و کلید امنیتی رو ذخیره نمی‌کنم.")
                return
            memory_id = self.db.remember(identity_id, arg)
            await update.reply(f"باشه، یادم می‌مونه. شمارهٔ خاطره: {memory_id}")
            return
        if command == "/memories":
            rows = self.db.memories(identity_id)
            await update.reply("\n".join(f"{mid}. {content}" for mid, content in rows) if rows else "هنوز خاطره‌ای ثبت نکردی.")
            return
        if command == "/forget":
            if not re.fullmatch(r"\d+", arg):
                await update.reply("روش استفاده: /forget شماره")
                return
            ok = self.db.forget_memory(identity_id, int(arg))
            await update.reply("حذف شد." if ok else "این خاطره پیدا نشد.")
            return
        if command == "/linkcode":
            code = self.db.create_link_code(identity_id)
            await update.reply(f"کد پیوند: {code}\nتا ۱۰ دقیقه در حساب خودت در پلتفرم دیگر دستور /link {code} را بفرست.")
            return
        if command == "/link":
            if not arg:
                await update.reply("روش استفاده: /link کد")
                return
            ok = self.db.redeem_link_code("rubika", sender, display, arg)
            await update.reply("حساب‌ها پیوند خوردند؛ خاطرات ثبت‌شده مشترک می‌شوند." if ok else "کد نامعتبر، منقضی یا ناسازگار است.")
            return
        if command == "/forgetme":
            deleted = self.db.forget_user("rubika", sender)
            await update.reply(f"خاطرات هویت پیوندخورده و {deleted} پیام تاریخچه از حساب‌های پیوندخورده پاک شد.")
            return

        is_private = chat_id.startswith("b0")
        addressed = is_private or bool(re.match(r"(?i)^\s*(مارکوس|marcus)(\b|[,،:!؟ ]|$)", text))
        if not addressed:
            return
        clean = re.sub(r"(?i)^\s*(مارکوس|marcus)\b[\s,،:!؟-]*", "", text).strip() or "یه چیزی بگو"
        self.db.add_message("rubika", chat_id, sender, "user", f"{display}: {clean}")
        history = self.db.history("rubika", chat_id, self.settings.max_history_messages)
        memories = [content for _, content in self.db.memories(identity_id, 15)]
        try:
            answer = await self.ai.reply(history, memories)
        except Exception:
            logger.exception("OpenRouter request failed for Rubika")
            answer = "الان به هوش مصنوعیم وصل نمی‌شم؛ یه کم دیگه امتحان کن."
        self.db.add_message("rubika", chat_id, sender, "assistant", answer)
        await update.reply(answer[:3500])

    def run(self) -> None:
        if not self.settings.rubika_bot_token:
            return
        try:
            from rubpy.bot import BotClient, filters
        except ImportError as exc:
            raise RuntimeError("برای اتصال روبیکا، نصب نسخهٔ Rubpy دارای BotClient کامل نشده است.") from exc
        app = BotClient(self.settings.rubika_bot_token)

        @app.on_update(filters.text)
        async def on_update(client, update):
            await self.handle(client, update)

        logger.info("Starting Rubika BotClient adapter")
        app.run()
