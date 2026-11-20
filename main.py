import json
import logging
import os
import re
from collections import Counter
from datetime import datetime

import emoji
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WELCOME_TEXT = """👋 Welcome to ChatLens!

Export a Telegram chat as a JSON file and send it here. I can show you:
📊 Message counts for each person
⏰ Your busiest days and hours
💬 Most used words and emojis

Send /guide for step-by-step export instructions.
"""

GUIDE_TEXT = """📥 How to export a Telegram chat as JSON

To export one chat:
1. Open Telegram Desktop on your computer.
2. Open the chat you want to analyze.
3. Click the three-dot menu ⋮ and choose “Export chat history”.
4. Select “Machine-readable JSON” as the format.
5. You can leave photos and videos unchecked if you only want message statistics.
6. Click Export and wait for Telegram to prepare the files.
7. Send the exported JSON file to this bot.

To export multiple chats:
Open Settings > Advanced > Export Telegram data, choose JSON, and export your data. Then send the relevant JSON file from the exported folder to this bot.

Note: Chat export is available in Telegram Desktop, not Telegram Web or the mobile app. If the file is too large, export one chat at a time.
"""

MAX_FILE_SIZE = 20 * 1024 * 1024

STOP_WORDS = {
    "the", "and", "you", "that", "for", "with", "this", "was", "are",
    "but", "have", "not", "your", "just", "from", "what", "about",
    "they", "their", "them", "then", "there", "here", "would", "could",
    "should", "will", "can", "all", "any", "how", "when", "where",
}


def extract_text(value) -> str:
    """Extract text from Telegram Desktop's JSON text formats."""
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
        return " ".join(part for part in parts if part)

    return ""


def get_chat_data(data: dict) -> tuple[str, list]:
    """Get messages from a single-chat or multi-chat Telegram export."""
    chats = data.get("chats")

    if isinstance(chats, dict):
        chat_list = chats.get("list", [])
        if isinstance(chat_list, list) and chat_list:
            messages = []
            names = []

            for chat in chat_list:
                if not isinstance(chat, dict):
                    continue

                chat_messages = chat.get("messages", [])
                if isinstance(chat_messages, list):
                    messages.extend(chat_messages)

                if chat.get("name"):
                    names.append(str(chat["name"]))

            title = ", ".join(names[:3])
            if len(names) > 3:
                title += f" and {len(names) - 3} more chats"

            return title or "Telegram chats", messages

    # Some single-chat exports have messages at the top level.
    messages = data.get("messages")
    if isinstance(messages, list):
        return str(data.get("name", "Telegram chat")), messages

    raise ValueError("The JSON structure is not a supported Telegram export.")


def analyze_messages(messages: list) -> dict:
    """Build message, date, word, and emoji statistics."""
    people = Counter()
    weekdays = Counter()
    hours = Counter()
    words = Counter()
    emojis = Counter()
    dated_messages = 0
    message_count = 0

    for message in messages:
        if not isinstance(message, dict):
            continue

        # Skip service events such as group photo changes.
        if message.get("type") not in (None, "message"):
            continue

        message_count += 1
        sender = message.get("from") or message.get("actor") or "Unknown"
        people[str(sender)] += 1

        raw_date = message.get("date")
        if raw_date:
            try:
                parsed_date = datetime.fromisoformat(
                    str(raw_date).replace("Z", "+00:00")
                )
                weekdays[parsed_date.strftime("%A")] += 1
                hours[parsed_date.hour] += 1
                dated_messages += 1
            except (TypeError, ValueError):
                pass

        text = extract_text(message.get("text"))
        if not text:
            continue

        for word in re.findall(r"[^\W\d_]+", text.casefold(), flags=re.UNICODE):
            if len(word) > 1 and word not in STOP_WORDS:
                words[word] += 1

        for item in emoji.emoji_list(text):
            emojis[item["emoji"]] += 1

    return {
        "message_count": message_count,
        "people": people,
        "weekdays": weekdays,
        "hours": hours,
        "words": words,
        "emojis": emojis,
        "dated_messages": dated_messages,
    }


def make_report(chat_name: str, stats: dict) -> str:
    """Format the analysis as a Telegram message."""
    lines = [
        f"📊 Analysis: {chat_name}",
        f"💬 Total messages: {stats['message_count']}",
        "",
        "👥 Messages by person:",
    ]

    for person, count in stats["people"].most_common(10):
        lines.append(f"• {person}: {count}")

    if stats["weekdays"]:
        day, count = stats["weekdays"].most_common(1)[0]
        lines.extend(["", f"📅 Busiest day: {day} ({count} messages)"])

    if stats["hours"]:
        hour, count = stats["hours"].most_common(1)[0]
        lines.append(
            f"🕒 Busiest hour: {hour:02d}:00–{hour:02d}:59 ({count} messages)"
        )

    if stats["words"]:
        top_words = ", ".join(
            f"{word} ({count})"
            for word, count in stats["words"].most_common(10)
        )
        lines.extend(["", f"🔤 Most used words: {top_words}"])

    if stats["emojis"]:
        top_emojis = " ".join(
            f"{symbol} ({count})"
            for symbol, count in stats["emojis"].most_common(10)
        )
        lines.extend(["", f"😀 Most used emojis: {top_emojis}"])

    if not stats["dated_messages"]:
        lines.extend([
            "",
            "⚠️ Message dates could not be read, so daily and hourly statistics are unavailable.",
        ])

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME_TEXT)


async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(GUIDE_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Send /guide for instructions on exporting a Telegram chat. "
            "Then send the JSON file here."
        )


async def handle_json(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.document:
        return

    document = message.document
    filename = document.file_name or ""

    if not filename.lower().endswith(".json"):
        await message.reply_text(
            "Please send a .json file. Send /guide for export instructions."
        )
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await message.reply_text(
            "This file is too large for this version. "
            "Please export one chat at a time and send its JSON file."
        )
        return

    try:
        telegram_file = await document.get_file()
        file_bytes = await telegram_file.download_as_bytearray()
        data = json.loads(file_bytes.decode("utf-8-sig"))

        if not isinstance(data, dict):
            raise ValueError("Invalid JSON structure.")

        chat_name, messages = get_chat_data(data)
        stats = analyze_messages(messages)
        await message.reply_text(make_report(chat_name, stats))

    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        logger.info("Could not parse uploaded JSON: %s", error)
        await message.reply_text(
            "I couldn't read this file. Please send the Telegram JSON export, "
            "not an HTML export or another file."
        )
    except Exception:
        logger.exception("Error while analyzing uploaded file")
        await message.reply_text(
            "Something went wrong while analyzing the file. Please try again."
        )


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        raise RuntimeError(
            "BOT_TOKEN is missing. Add your bot token to the .env file."
        )

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("guide", guide))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_json))

    logger.info("ChatLens bot is starting")
    app.run_polling()


if __name__ == "__main__":
    main()