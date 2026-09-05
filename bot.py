import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv
import os

from handlers.commands import start, status, natija
from handlers.admin import post_manual, handle_admin_media, admin_callback, transfer_post, news_post
from services.scheduler import setup_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN .env faylda ko'rsatilishi shart.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def post_init(app):
    await setup_scheduler(app)

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holat", status))
    app.add_handler(CommandHandler("natija", natija))
    app.add_handler(CommandHandler("post", post_manual))
    app.add_handler(CommandHandler("transfer", transfer_post))
    app.add_handler(CommandHandler("xabar", news_post))

    # Admin yuborgan photo/video/document uchun
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.Document.ALL,
            handle_admin_media
        )
    )
    app.add_handler(CallbackQueryHandler(admin_callback))

    logging.info("🇺🇿 Uzbek Football Media Bot ishga tushdi.")
    app.run_polling()

if __name__ == "__main__":
    main()
