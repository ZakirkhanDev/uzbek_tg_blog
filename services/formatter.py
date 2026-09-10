from html import escape
import random

CHANNEL_LINK = "@otabekzokirov1"

FIXTURE_INTROS = [
    "☀️ Bugungi o‘yinlar tayyor!",
    "⚽ Bugun maydonlarda katta futbol!",
    "📅 Bugungi futbol taqvimi.",
]

RESULTS_INTROS = [
    "🌙 Kun yakuni.",
    "🏁 Bugungi final natijalar.",
    "📋 Maydondagi kun yakuni.",
]


def with_footer(text):
    return f"{text}\n\n{CHANNEL_LINK}"


def daily_fixtures_header(date_label=""):
    title = f"📅 <b>{escape(date_label)} o‘yinlari</b>" if date_label else "📅 <b>Bugungi o‘yinlar jadvali</b>"
    return f"{random.choice(FIXTURE_INTROS)}\n{title}\n"


def daily_results_header():
    return f"{random.choice(RESULTS_INTROS)}\n🏁 <b>Bugungi natijalar</b>\n"


def news_caption(title, body, source=None):
    text = f"📰 <b>{escape(title)}</b>\n\n{escape(body)}"
    if source:
        text += f"\n\n📝 Manba: {escape(source)}"
    return with_footer(text)


def transfer_caption(player, old_club, new_club, details="", source=None):
    text = (
        "🔄 <b>TRANSFER</b>\n\n"
        f"👤 <b>{escape(player)}</b>\n"
        f"{escape(old_club)} ➡️ {escape(new_club)}"
    )
    if details:
        text += f"\n\n{escape(details)}"
    if source:
        text += f"\n\n📝 Manba: {escape(source)}"
    return with_footer(text)


def result_caption(match):
    home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")
    score = match.get("score", {}).get("fullTime", {})
    hs = 0 if score.get("home") is None else score.get("home")
    aws = 0 if score.get("away") is None else score.get("away")
    competition = (match.get("competition") or {}).get("name", "Futbol")
    lines = [f"🏁 <b>{escape(home)} {hs} : {aws} {escape(away)}</b>", f"🏆 {escape(competition)}"]
    events = match.get("events") or []
    scorers = [e for e in events if e.get("scorer")]
    if scorers:
        lines.append("")
        for e in scorers[:8]:
            minute = f"{e['minute']}' " if e.get("minute") else ""
            lines.append(f"⚽ {minute}{escape(e['scorer'])}")
    return with_footer("\n".join(lines))


def standings_caption(competition_name, table, limit=10):
    lines = [f"📊 <b>{escape(competition_name)} — Turnir jadvali</b>\n"]
    for row in table[:limit]:
        pos = row.get("position")
        team = row.get("team", {}).get("shortName") or row.get("team", {}).get("name", "")
        pts = row.get("points")
        played = row.get("playedGames")
        lines.append(f"{pos}. {escape(str(team))} — {pts} ochko ({played} o‘yin)")
    return with_footer("\n".join(lines))


def star_player_caption(name, club="", info=""):
    text = f"⭐ <b>{escape(name)}</b>"
    if club:
        text += f"\n🏟 {escape(club)}"
    if info:
        text += f"\n\n{escape(info)}"
    return with_footer(text)
