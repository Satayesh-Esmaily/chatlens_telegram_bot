import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WELCOME_TEXT = """👋 Welcome to ChatLens!

See your chats in a whole new way. Export a chat from Telegram Desktop, send me the file, and I'll show you:
📊 Message counts for each person
⏰ Your busiest days and hours
💬 Most used words and emojis

Plus: reminders ⏰, notes 📝 and quick replies ⚡

100% free. Your data stays private."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Send /start to see what ChatLens can do. "
            "Chat analysis is coming soon."
        )


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        raise RuntimeError(
            "BOT_TOKEN is missing. Add your Telegram bot token to the .env file."
        )

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("ChatLens bot is starting")
    app.run_polling()


if __name__ == "__main__":
    main()