from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.football_api import fetch_matches, format_match, fetch_standings, COMPETITION_NAMES
from services import api_football
from services.formatter import standings_caption

LEAGUE_BUTTONS = [
    ("🇬🇧 Premier League", "PL"),
    ("🇪🇸 La Liga", "PD"),
    ("🇮🇹 Serie A", "SA"),
    ("🇩🇪 Bundesliga", "BL1"),
    ("🇫🇷 Ligue 1", "FL1"),
    ("🇺🇸 MLS", "MLS"),
    ("🇺🇿 O‘zbekiston Super League", "UZS"),
]

RESULT_BUTTONS = LEAGUE_BUTTONS + [("🏆 UEFA Champions League", "CL")]

FIXTURE_BUTTONS = RESULT_BUTTONS

async def fixtures_results_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌅 Ertalabki fixtures", callback_data="fx:morning")],
        [InlineKeyboardButton("🌙 Kechki results", callback_data="fx:results")],
        [InlineKeyboardButton("❌ Yopish", callback_data="fx:close")],
    ]
    await query.edit_message_text(
        "📅 <b>Fixtures & Results</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def fixtures_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "fx_menu":
        await fixtures_results_menu(update, context)
        return

    if data == "fx:close":
        await query.edit_message_text("📅 Fixtures & Results menyusi yopildi.")
        return

    if data == "fx:morning":
        matches = fetch_today_matches()
        matches += api_football.fetch_today_matches()
        unique = {}
        for m in matches:
            if m.get("id") is not None:
                unique[str(m["id"])] = m
        scheduled = [
            m for m in unique.values()
            if m.get("status") in {"SCHEDULED", "TIMED"}
        ]
        scheduled.sort(key=lambda m: m.get("utcDate", ""))

        keyboard = [[InlineKeyboardButton("🔙 Fixtures & Results", callback_data="fx_menu")]]
        if not scheduled:
            await query.edit_message_text(
                "❌ Bugun uchun rejalashtirilgan fixture topilmadi.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        from services.football_api import group_and_format_fixtures, today_uz_date_label
        text = (
            f"🌅 <b>Ertalabki fixtures — {today_uz_date_label()}</b>\n\n"
            + group_and_format_fixtures(scheduled)
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "fx:results":
        await results_menu(update, context)
        return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Fixtures & Results", callback_data="fx_menu")],
        [InlineKeyboardButton("📊 Ligalar jadvallari", callback_data="standings_menu")],
    ]
    await update.message.reply_text(
        "🇺🇿 Salom! Men futbol media kanal botiman.\n\n"
        "/natija — jonli o'yinlar\n"
        "/holat — bot holati\n"
        "/post Matn — admin post",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot ishlamoqda.")

async def natija(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_matches("LIVE") + api_football.fetch_live_matches()
    if not matches:
        await update.message.reply_text("🔴 Hozircha jonli o'yin topilmadi.")
        return
    text = "\n\n".join(format_match(m) for m in matches[:10])
    await update.message.reply_text(text, parse_mode="HTML")

async def standings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"standings:{code}")]
        for name, code in LEAGUE_BUTTONS
    ]
    keyboard.append([InlineKeyboardButton("❌ Yopish", callback_data="standings_close")])
    await query.edit_message_text(
        "📊 <b>Liga jadvalini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def league_standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "standings_menu":
        await standings_menu(update, context)
        return

    if data == "standings_close":
        await query.edit_message_text("📊 Liga jadvallari menyusi yopildi.")
        return

    if not data.startswith("standings:"):
        return

    code = data.split(":", 1)[1]
    names = dict(LEAGUE_BUTTONS)
    competition_name = names.get(code)
    if not competition_name:
        return

    await query.edit_message_text("⏳ Jadval yuklanmoqda...")

    if code in {"PL", "PD", "SA", "BL1", "FL1"}:
        table = fetch_standings(code)
    elif code == "MLS":
        table = api_football.fetch_standings("USA", "MLS")
    elif code == "UZS":
        table = api_football.fetch_standings("Uzbekistan", "Super League")
    else:
        table = []

    if not table:
        keyboard = [[InlineKeyboardButton("🔙 Ligalar", callback_data="standings_menu")]]
        await query.edit_message_text(
            f"❌ <b>{competition_name}</b> jadvali hozircha olinmadi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    text = standings_caption(competition_name, table, limit=20)
    keyboard = [[InlineKeyboardButton("🔙 Ligalar", callback_data="standings_menu")]]
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def results_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"results:{code}")]
        for name, code in RESULT_BUTTONS
    ]
    keyboard.append([InlineKeyboardButton("❌ Yopish", callback_data="results_close")])
    await query.edit_message_text(
        "🏁 <b>Final natijalar — ligani tanlang:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def league_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "results_menu":
        await results_menu(update, context)
        return

    if data == "results_close":
        await query.edit_message_text("🏁 Final natijalar menyusi yopildi.")
        return

    if not data.startswith("results:"):
        return

    code = data.split(":", 1)[1]
    names = dict(RESULT_BUTTONS)
    competition_name = names.get(code)
    if not competition_name:
        return

    await query.edit_message_text("⏳ Natijalar yuklanmoqda...")

    if code in {"PL", "PD", "SA", "BL1", "FL1", "CL"}:
        matches = fetch_today_matches(status="FINISHED")
        matches = [m for m in matches if m.get("competition", {}).get("code") == code]
    elif code == "MLS":
        matches = [m for m in api_football.fetch_today_matches()
                   if m.get("status") == "FINISHED" and m.get("competition", {}).get("code") == "MLS"]
    elif code == "UZS":
        matches = [m for m in api_football.fetch_today_matches()
                   if m.get("status") == "FINISHED" and m.get("competition", {}).get("code") == "UZS"]
    else:
        matches = []

    keyboard = [[InlineKeyboardButton("🔙 Natijalar", callback_data="results_menu")]]
    if not matches:
        await query.edit_message_text(
            f"❌ <b>{competition_name}</b> uchun bugun yakunlangan o'yin topilmadi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    lines = [f"🏁 <b>{competition_name} — Bugungi final natijalar</b>\n"]
    lines.extend(format_match(m) for m in matches)
    await query.edit_message_text(
        "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
