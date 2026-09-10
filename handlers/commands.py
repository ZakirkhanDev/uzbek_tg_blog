from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.football_api import (
    fetch_matches, fetch_today_matches, format_match, fetch_standings,
    COMPETITION_NAMES, group_and_format_fixtures, today_uz_date_label,
)
from services import api_football
from services.formatter import standings_caption
from services.keyboards import LEAGUE_BUTTONS, RESULT_BUTTONS, channel_main_keyboard, fixtures_menu_keyboard, league_keyboard


def _unique(matches):
    out = {}
    for m in matches:
        if m.get("id") is not None:
            out[str(m["id"])] = m
    return list(out.values())


async def fixtures_results_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📅 <b>Fixtures & Results</b>\n\nKerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=fixtures_menu_keyboard(),
    )


async def fixtures_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "fx_menu":
        await fixtures_results_menu(update, context)
        return
    if data == "fx:close":
        await query.edit_message_text("📅 Fixtures & Results yopildi.")
        return
    if data == "fx:fixtures":
        await query.edit_message_text("⏳ Bugungi fixtures yuklanmoqda...")
        try:
            matches = _unique(fetch_today_matches() + api_football.fetch_today_matches())
            scheduled = [m for m in matches if m.get("status") in {"SCHEDULED", "TIMED"}]
            if not scheduled:
                text = "❌ Bugun uchun fixture topilmadi."
            else:
                text = f"📅 <b>Bugungi fixtures — {today_uz_date_label()}</b>\n\n{group_and_format_fixtures(scheduled)}"
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="fx_menu")]]))
        except Exception as e:
            await query.edit_message_text(f"❌ Xatolik: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="fx_menu")]]))
        return
    if data == "fx:results":
        await results_menu(update, context)
        return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇺🇿 <b>Otabek Zokirov Blogi</b>\n\n"
        "Futbol yangiliklari, fixtures, final natijalar va turnir jadvallari.",
        parse_mode="HTML",
        reply_markup=channel_main_keyboard(),
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot ishlamoqda.")


async def natija(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_matches("LIVE") + api_football.fetch_live_matches()
    if not matches:
        await update.message.reply_text("🔴 Hozircha jonli o‘yin topilmadi.")
        return
    text = "\n\n".join(format_match(m) for m in _unique(matches)[:10])
    await update.message.reply_text(text, parse_mode="HTML")


async def standings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 <b>Turnir jadvalini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=league_keyboard("standings", RESULT_BUTTONS),
    )


async def league_standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()
    if data == "standings_menu":
        await standings_menu(update, context)
        return
    if data == "standings_close":
        await query.edit_message_text("📊 Standings yopildi.")
        return
    if not data.startswith("standings:"):
        return
    code = data.split(":", 1)[1]
    names = dict(RESULT_BUTTONS)
    competition_name = names.get(code)
    if not competition_name:
        return
    await query.edit_message_text("⏳ Jadval yuklanmoqda...")
    try:
        if code in {"PL", "PD", "SA", "BL1", "FL1", "CL"}:
            table = fetch_standings(code)
            if not table and code == "CL":
                table = api_football.fetch_standings("World", "UEFA Champions League")
        elif code == "MLS":
            table = api_football.fetch_standings("USA", "MLS")
        elif code == "UZS":
            table = api_football.fetch_standings("Uzbekistan", "Super League")
        else:
            table = []
        if not table:
            text = f"❌ <b>{competition_name}</b> jadvali hozircha olinmadi."
        else:
            text = standings_caption(competition_name, table, limit=20)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ligalar", callback_data="standings_menu")]]))
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ligalar", callback_data="standings_menu")]]))


async def results_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏁 <b>Final natijalar — ligani tanlang:</b>",
        parse_mode="HTML",
        reply_markup=league_keyboard("results", RESULT_BUTTONS),
    )


async def league_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()
    if data == "results_menu":
        await results_menu(update, context)
        return
    if data == "results_close":
        await query.edit_message_text("🏁 Results yopildi.")
        return
    if not data.startswith("results:"):
        return
    code = data.split(":", 1)[1]
    names = dict(RESULT_BUTTONS)
    competition_name = names.get(code)
    if not competition_name:
        return
    await query.edit_message_text("⏳ Natijalar yuklanmoqda...")
    try:
        matches = _unique(fetch_today_matches() + api_football.fetch_today_matches())
        matches = [m for m in matches if m.get("status") == "FINISHED" and m.get("competition", {}).get("code") == code]
        if not matches:
            text = f"❌ <b>{competition_name}</b> uchun bugun yakunlangan o‘yin topilmadi."
        else:
            lines = [f"🏁 <b>{competition_name} — {today_uz_date_label()}</b>"]
            lines.extend(format_match(m) for m in matches)
            text = "\n\n".join(lines)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Natijalar", callback_data="results_menu")]]))
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Natijalar", callback_data="results_menu")]]))
