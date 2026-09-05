from telegram import Update
from telegram.ext import ContextTypes
from services.football_api import fetch_matches, format_match

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇺🇿 Salom! Men futbol media kanal botiman.\n\n"
        "/natija — jonli o'yinlar\n"
        "/holat — bot holati\n"
        "/post Matn — admin post"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot ishlamoqda.")

async def natija(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_matches("LIVE")
    if not matches:
        await update.message.reply_text("🔴 Hozircha jonli o'yin topilmadi.")
        return

    text = "\n\n".join(format_match(m) for m in matches[:10])
    await update.message.reply_text(text, parse_mode="HTML")
