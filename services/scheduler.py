import os
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.football_api import (
    fetch_matches, format_match, fetch_today_matches,
    is_top_club, is_uz_top_club, ALL_COMPETITIONS, COMPETITION_NAMES,
    fetch_match_detail, goal_scorer_for_score,
    group_and_format_fixtures, today_uz_date_label
)
from services import api_football
from services.formatter import (
    goal_caption, daily_fixtures_header, daily_results_header, with_footer
)
from database.db import init_db, was_posted, mark_posted, get_last_score, set_last_score

async def check_live(app):
    matches = fetch_matches("LIVE") + api_football.fetch_live_matches()
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    for match in matches:
        match_id = match.get("id")
        if not match_id:
            continue

        home_name = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
        away_name = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")

        # Faqat top klublar (yoki O'zbekiston Superligasining Navbahor/Pakhtakor/Neftchi/Nasaf) ishtirok etadigan o'yinlar
        if not (
            is_top_club(home_name) or is_top_club(away_name)
            or is_uz_top_club(home_name) or is_uz_top_club(away_name)
        ):
            continue

        status = match.get("status", "UNKNOWN")
        score = match.get("score", {}).get("fullTime", {})
        home_score = score.get("home") or 0
        away_score = score.get("away") or 0

        key = f"live:{match_id}:{home_score}:{away_score}"
        if was_posted(key):
            continue

        last = get_last_score(match_id)
        is_goal = (
            last is not None
            and (home_score, away_score) != tuple(last)
            and (home_score > last[0] or away_score > last[1])
        )

        try:
            if is_goal:
                code = match.get("competition", {}).get("code", "")
                competition = COMPETITION_NAMES.get(code) or match.get("competition", {}).get("name", "Futbol")

                # Gol muallifi va assistni aniqlashga harakat qilamiz (match detail orqali)
                scorer, assist = None, None
                if str(match_id).startswith("af_"):
                    detail = api_football.fetch_match_detail(match_id)
                    if detail:
                        scorer, assist = api_football.goal_scorer_for_score(
                            detail, home_score, away_score, last[0], last[1]
                        )
                else:
                    detail = fetch_match_detail(match_id)
                    if detail:
                        scorer, assist = goal_scorer_for_score(
                            detail, home_score, away_score, last[0], last[1]
                        )

                caption = goal_caption(
                    competition, home_name, away_name, home_score, away_score,
                    scorer=scorer, assist=assist
                )
                # Talab bo'yicha: giant klub gol postlari rasmsiz, faqat matn
                await app.bot.send_message(chat_id=channel, text=caption, parse_mode="HTML")
            else:
                await app.bot.send_message(
                    chat_id=channel, text=with_footer(format_match(match)), parse_mode="HTML"
                )

            mark_posted(key)
        except Exception:
            pass

        set_last_score(match_id, home_score, away_score)

async def post_daily_fixtures(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    matches = fetch_today_matches() + api_football.fetch_today_matches()
    scheduled = [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]
    if not scheduled:
        return

    header = daily_fixtures_header(today_uz_date_label())
    body = group_and_format_fixtures(scheduled)
    text = with_footer(f"{header}\n{body}")

    try:
        await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
    except Exception:
        pass

async def post_daily_results_and_standings(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    # Natijalarni barcha futbol o'yinlari tugagandan keyin bitta post qilib yuboramiz.
    all_today = fetch_today_matches() + api_football.fetch_today_matches()
    if not all_today:
        return

    # Bir xil o'yin ikki manbadan kelib qolsa, ID bo'yicha dublikatni olib tashlaymiz.
    unique = {}
    for m in all_today:
        if m.get("id") is not None:
            unique[str(m["id"])] = m
    all_today = list(unique.values())

    # Hali boshlanmagan yoki davom etayotgan o'yin bo'lsa, keyingi tekshiruvni kutamiz.
    remaining = [
        m for m in all_today
        if m.get("status") in {"SCHEDULED", "TIMED", "LIVE", "PAUSED"}
    ]
    if remaining:
        return

    finished = [m for m in all_today if m.get("status") == "FINISHED"]
    if not finished:
        return

    # Bugungi yakuniy post faqat bir marta yuboriladi.
    today_key = today_uz_date_label()
    post_key = f"daily_final_results:{today_key}"
    if was_posted(post_key):
        return

    # Natijalarni musobaqa bo'yicha guruhlab, bitta ixcham post qilamiz.
    grouped = {}
    for m in finished:
        code = m.get("competition", {}).get("code", "")
        name = COMPETITION_NAMES.get(code) or m.get("competition", {}).get("name", "Futbol")
        grouped.setdefault(name, []).append(m)

    lines = [daily_results_header()]
    for competition, matches in sorted(grouped.items()):
        lines.append(f"🏆 <b>{competition}</b>")
        for m in matches:
            lines.append(format_match(m))
        lines.append("")

    text = with_footer("\n".join(lines).rstrip())
    try:
        await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        mark_posted(post_key)
    except Exception:
        pass

async def setup_scheduler(app):
    init_db()
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))

    scheduler.add_job(
        check_live, "interval", minutes=1, args=[app],
        id="live_scores", replace_existing=True
    )
    scheduler.add_job(
        post_daily_fixtures, "cron", hour=8, minute=0, args=[app],
        id="daily_fixtures", replace_existing=True
    )
    # Kechki yakuniy natijalarni futbol tugaguncha har 15 daqiqada tekshiramiz.
    # Barcha bugungi o'yinlar FINISHED bo'lgach, faqat bir marta bitta post yuboriladi.
    scheduler.add_job(
        post_daily_results_and_standings, "interval", minutes=15, args=[app],
        id="daily_final_results", replace_existing=True
    )

    scheduler.start()
