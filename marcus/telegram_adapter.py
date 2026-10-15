import logging
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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"سلام، من {self.settings.bot_name}‌ام! توی گروه منو صدا کن یا به پیامم ریپلای بزن."
            )

    async def forgetme(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not update.effective_message:
            return
        deleted = self.db.forget_user(str(user.id))
        await update.effective_message.reply_text(
            f"تاریخچهٔ ذخیره‌شدهٔ قابل‌شناسایی برای این حساب پاک شد ({deleted} پیام)."
        )

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        if not message or not user or not chat or not message.text:
            return
        if user.is_bot:
            return

        bot = context.bot
        addressed = False
        if chat.type == "private":
            addressed = True
        else:
            me = await bot.get_me()
            mention = f"@{me.username}" if me.username else ""
            addressed = bool(
                (mention and mention.lower() in message.text.lower())
                or (message.reply_to_message and message.reply_to_message.from_user
                    and message.reply_to_message.from_user.id == me.id)
                or message.text.lower().startswith(("مارکوس", "marcus"))
            )
        if not addressed:
            return

        clean_text = message.text
        me = await bot.get_me()
        if me.username:
            clean_text = clean_text.replace(f"@{me.username}", "").strip()
        clean_text = clean_text.removeprefix("مارکوس").removeprefix("marcus").strip(" ,،:!؟")
        if not clean_text:
            clean_text = "یه چیزی بگو"

        chat_id = str(chat.id)
        user_id = str(user.id)
        self.db.add_message(chat_id, user_id, "user", clean_text)
        history = self.db.history(chat_id, self.settings.max_history_messages)
        try:
            answer = await self.ai.reply(history)
        except Exception:
            logger.exception("OpenRouter request failed")
            answer = "الان به هوش مصنوعیم وصل نمی‌شم؛ یه کم دیگه امتحان کن."
        self.db.add_message(chat_id, user_id, "assistant", answer)
        for start in range(0, len(answer), 4000):
            await message.reply_text(answer[start:start + 4000])

    def build(self) -> Application:
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("forgetme", self.forgetme))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))
        return app
