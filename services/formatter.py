from html import escape
import random

CHANNEL_LINK = "@otabekzokirov1"

def with_footer(text):
    """Katta/regular postlarning eng tagiga joy tashlab kanal linkini qo'shadi."""
    return f"{text}\n\n{CHANNEL_LINK}"

FIXTURE_INTROS = [
    "🌅 Xayrli tong, o'rtoqlar!",
    "☀️ Yangi kun — bugungi o'yinlar!",
    "🔥 Bugun stadionlarda horarat qizg'in bo'ladi!",
    "⚽ Bugungi jadval tayyor!",
]

RESULTS_INTROS = [
    "🌙 Kun yakuni — natijalar!",
    "🏁 Bugungi o'yinlar tugadi, xulosa!",
    "📋 Kechki hisobot — kim kimni yengdi?",
]

GOAL_HYPE = ["GOOOOL!", "TOOOOP!", "Vuuuuuh!!!", "GOOOOL, AYAB o'tirmadi!"]

def daily_fixtures_header():
    return f"{random.choice(FIXTURE_INTROS)}\n📅 <b>Bugungi o'yinlar jadvali</b>\n"

def daily_results_header():
    return f"{random.choice(RESULTS_INTROS)}\n🏁 <b>Bugungi natijalar</b>\n"

def news_caption(title, body, source=None):
    text = f"📰 <b>{escape(title)}</b>\n\n{escape(body)}"
    if source:
        text += f"\n\n📝 Manba: {escape(source)}"
    return with_footer(text)

def transfer_caption(player, old_club, new_club, details="", source=None):
    text = (
        "🚨 <b>TRANSFER</b>\n\n"
        f"👤 <b>{escape(player)}</b>\n"
        f"🔄 {escape(old_club)} ➡️ {escape(new_club)}\n"
    )
    if details:
        text += f"\n{escape(details)}"
    if source:
        text += f"\n\n📝 Manba: {escape(source)}"
    return with_footer(text)

def goal_caption(competition, home, away, home_score, away_score, scorer=None, assist=None, minute=None):
    text = (
        f"🚨 <b>{random.choice(GOAL_HYPE)}</b>\n\n"
        f"🏆 {escape(competition)}\n"
        f"⚽ {escape(home)} <b>{home_score} : {away_score}</b> {escape(away)}"
    )
    if scorer:
        line = f"\n\n⚽ Gol muallifi: <b>{escape(scorer)}</b>"
        if minute:
            line += f" — {minute}'"
        text += line
        if assist:
            text += f"\n🎯 Assist: <b>{escape(assist)}</b>"
    return with_footer(text)

def standings_caption(competition_name, table, limit=10):
    lines = [f"📊 <b>{escape(competition_name)} — Turnir jadvali</b>\n"]
    for row in table[:limit]:
        pos = row.get("position")
        team = row.get("team", {}).get("shortName") or row.get("team", {}).get("name", "")
        pts = row.get("points")
        played = row.get("playedGames")
        lines.append(f"{pos}. {escape(str(team))} — {pts} ochko ({played} o'yin)")
    return with_footer("\n".join(lines))

def star_player_caption(name, club="", info=""):
    """Yulduz futbolchi haqida rasmli post uchun format.
    Admin rasmga caption sifatida yozadi: ⭐ Ism | Klub | Ma'lumot/yangilik
    """
    text = f"⭐ <b>{escape(name)}</b>"
    if club:
        text += f"\n🏟 {escape(club)}"
    if info:
        text += f"\n\n{escape(info)}"
    return with_footer(text)
