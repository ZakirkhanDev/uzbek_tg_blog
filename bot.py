import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from handlers.commands import (
    start, status, natija, league_standings_callback,
    league_results_callback, fixtures_results_callback,
)
from handlers.admin import (
    post_manual, handle_admin_media, admin_callback, transfer_post,
    news_post, test_fixtures, test_results,
)
from services.scheduler import setup_scheduler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN .env faylda ko‘rsatilishi shart.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


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
    app.add_handler(CommandHandler("test_jadval", test_fixtures))
    app.add_handler(CommandHandler("test_natija", test_results))

    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_admin_media))

    # Channel/private callbacks: exact menu patterns are included so the buttons never hang.
    app.add_handler(CallbackQueryHandler(league_standings_callback, pattern=r"^(standings_menu|standings:.*|standings_close)$"))
    app.add_handler(CallbackQueryHandler(fixtures_results_callback, pattern=r"^fx(?:_menu|:.*)$"))
    app.add_handler(CallbackQueryHandler(league_results_callback, pattern=r"^(results_menu|results:.*|results_close)$"))
    app.add_handler(CallbackQueryHandler(admin_callback))

    logging.info("🇺🇿 Otabek Zokirov Blogi — Professional V4 ishga tushdi.")
    app.run_polling()


if __name__ == "__main__":
    main()
