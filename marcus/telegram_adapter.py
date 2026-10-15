import logging
import random
import re
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from .ai import OpenRouterClient
from .config import Settings
from .db import Database

logger = logging.getLogger(__name__)

class TelegramAdapter:
    def __init__(self, settings: Settings, db: Database, ai: OpenRouterClient):
        self.settings = settings
        self.db = db
        self.ai = ai
        self.last_reply_at: dict[str, float] = {}

    async def private_only(self, update: Update) -> bool:
        chat = update.effective_chat
        if chat and chat.type != "private":
            if update.effective_message:
                await update.effective_message.reply_text("برای حفظ حریم خصوصی، این دستور رو توی چت خصوصی با خودم بفرست.")
            return False
        return True

    def identity(self, update: Update) -> tuple[str, str, str]:
        user = update.effective_user
        if not user:
            raise ValueError("کاربر مشخص نیست")
        user_id = str(user.id)
        display = user.full_name or user.username or user_id
        return user_id, display, self.db.ensure_identity("telegram", user_id, display)

    def interesting_message(self, text: str) -> bool:
        lowered = text.lower()
        cues = ("؟", "?", "نظرتون", "به نظرت", "کسی میدونه", "کسی می‌دونه",
                "کمک می‌کنه", "کمک میکنه", "چطوره", "چرا", "چطور", "بهترین", "کدوم بهتره",
                "تجربه‌ای", "تجربه ای", "پیشنهاد", "راهنمایی")
        return len(text.strip()) >= 12 and any(cue in lowered for cue in cues)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"سلام، من {self.settings.bot_name}‌ام! توی گروه منو با «مارکوس» یا منشن صدا کن.\n"
                "دستورها: /remember، /memories، /forget، /linkcode، /link، /forgetme"
            )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "من مارکوسم، رفیق گروه.\n"
                "/remember متن — ذخیرهٔ یک خاطره با اجازهٔ خودت\n"
                "/memories — دیدن خاطرات ثبت‌شده\n"
                "/forget شماره — حذف یک خاطره\n"
                "/linkcode — ساخت کد ۱۰ دقیقه‌ای برای پیوند حساب روبیکا/تلگرام\n"
                "/link کد — پیوند این حساب با کد حساب دیگه\n"
                "/forgetme — حذف خاطرات و تاریخچهٔ قابل‌شناسایی تو"
            )

    async def remember(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message:
            return
        if not await self.private_only(update):
            return
        _, _, identity_id = self.identity(update)
        content = " ".join(context.args).strip()
        if not content:
            await update.effective_message.reply_text("بعد از دستور، چیزی که می‌خوای یادم بمونه رو بنویس.")
            return
        if re.search(r"(?i)(password|passcode|api[_ -]?key|token|رمز عبور|رمز کارت|کلید api)", content):
            await update.effective_message.reply_text("چیزهایی مثل رمز و کلید امنیتی رو ذخیره نمی‌کنم.")
            return
        memory_id = self.db.remember(identity_id, content)
        await update.effective_message.reply_text(f"باشه، یادم می‌مونه. شمارهٔ خاطره: {memory_id}")

    async def memories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message:
            return
        if not await self.private_only(update):
            return
        _, _, identity_id = self.identity(update)
        rows = self.db.memories(identity_id)
        if not rows:
            await update.effective_message.reply_text("هنوز خاطره‌ای ثبت نکردی. با /remember ثبت کن.")
            return
        await update.effective_message.reply_text("\n".join(f"{mid}. {content}" for mid, content in rows))

    async def forget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message:
            return
        if not await self.private_only(update):
            return
        _, _, identity_id = self.identity(update)
        if not context.args or not context.args[0].isdigit():
            await update.effective_message.reply_text("روش استفاده: /forget شماره")
            return
        removed = self.db.forget_memory(identity_id, int(context.args[0]))
        await update.effective_message.reply_text("حذف شد." if removed else "این شماره از خاطراتت پیدا نشد.")

    async def linkcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message:
            return
        if not await self.private_only(update):
            return
        _, _, identity_id = self.identity(update)
        code = self.db.create_link_code(identity_id)
        await update.effective_message.reply_text(
            f"کد پیوند: {code}\nاین کد ۱۰ دقیقه اعتبار دارد. در حساب خودت روی پلتفرم دیگر دستور /link {code} را بفرست. کد را برای کسی که نمی‌شناسی نفرست."
        )

    async def link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message or not update.effective_user:
            return
        if not await self.private_only(update):
            return
        if not context.args:
            await update.effective_message.reply_text("روش استفاده: /link کد")
            return
        user = update.effective_user
        display = user.full_name or user.username or str(user.id)
        ok = self.db.redeem_link_code("telegram", str(user.id), display, context.args[0])
        if ok:
            await update.effective_message.reply_text("حساب‌ها پیوند خوردند؛ از این به بعد خاطرات ثبت‌شده‌ات بین این دو حساب مشترک است.")
        else:
            await update.effective_message.reply_text("کد نامعتبر، منقضی یا ناسازگار است.")

    async def forgetme(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message or not update.effective_user:
            return
        if not await self.private_only(update):
            return
        user_id = str(update.effective_user.id)
        deleted = self.db.forget_user("telegram", user_id)
        await update.effective_message.reply_text(
            f"خاطرات هویت پیوندخورده و {deleted} پیام تاریخچه از حساب‌های پیوندخورده پاک شد."
        )

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        if not message or not user or not chat or not message.text or user.is_bot:
            return
        me = context.bot_data.get("marcus_me")
        if me is None:
            me = await context.bot.get_me()
            context.bot_data["marcus_me"] = me
        text = message.text.strip()
        addressed = chat.type == "private"
        if chat.type != "private":
            mention = f"@{me.username}" if me.username else ""
            addressed = bool(
                (mention and mention.lower() in text.lower())
                or (message.reply_to_message and message.reply_to_message.from_user
                    and message.reply_to_message.from_user.id == me.id)
                or re.match(r"(?i)^\s*(маркус|marcus|مارکوس)(\b|[,،:!؟ ]|$)", text)
            )
            if (not addressed and self.settings.proactive_replies
                    and self.interesting_message(text)
                    and random.random() < self.settings.proactive_probability):
                key = str(chat.id)
                now = time.monotonic()
                if now - self.last_reply_at.get(key, 0) >= self.settings.reply_cooldown_seconds:
                    addressed = True
        if not addressed:
            return

        clean_text = re.sub(rf"@{re.escape(me.username)}\b", "", text, flags=re.I).strip()
        clean_text = re.sub(r"(?i)^\s*(маркус|marcus|مارکوس)\b[\s,،:!؟-]*", "", clean_text).strip()
        if not clean_text:
            clean_text = "یه چیزی بگو"

        user_id, display, identity_id = self.identity(update)
        chat_id = str(chat.id)
        if re.search(r"یادت\s*(?:باشه|بمونه|نره)|(?:اینا|اینو|اینارو|این‌ها رو)\s*یادت", clean_text):
            if not re.search(r"(?i)(password|passcode|api[_ -]?key|token|رمز عبور|رمز کارت|کلید api)", clean_text):
                self.db.remember(identity_id, clean_text)
        self.db.add_message("telegram", chat_id, user_id, "user", f"{display}: {clean_text}")
        history = self.db.history("telegram", chat_id, self.settings.max_history_messages)
        memories = [content for _, content in self.db.memories(identity_id, 15)]
        try:
            answer = await self.ai.reply(history, memories)
        except Exception:
            logger.exception("OpenRouter request failed")
            answer = "الان به هوش مصنوعیم وصل نمی‌شم؛ یه کم دیگه امتحان کن."
        if not isinstance(answer, str) or not answer.strip() or answer.strip().casefold() in {"none", "null"}:
            answer = "این بار مدل جواب متنی نداد؛ یه بار دیگه بپرس."
        else:
            answer = answer.strip()
        self.db.add_message("telegram", chat_id, user_id, "assistant", answer)
        self.last_reply_at[chat_id] = time.monotonic()
        for start in range(0, len(answer), 4000):
            await message.reply_text(answer[start:start + 4000])

    def build(self) -> Application:
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("remember", self.remember))
        app.add_handler(CommandHandler("memories", self.memories_command))
        app.add_handler(CommandHandler("forget", self.forget))
        app.add_handler(CommandHandler("linkcode", self.linkcode))
        app.add_handler(CommandHandler("link", self.link))
        app.add_handler(CommandHandler("forgetme", self.forgetme))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))
        return app
