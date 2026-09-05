import os
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.football_api import (
    fetch_matches, format_match, fetch_today_matches, fetch_standings,
    format_fixture, is_top_club, ALL_COMPETITIONS, COMPETITION_NAMES,
    fetch_match_detail, last_goal_scorer_assist
)
from services.formatter import (
    goal_caption, standings_caption, daily_fixtures_header, daily_results_header, with_footer
)
from services.graphics import make_standings_graphic
from database.db import init_db, was_posted, mark_posted, get_last_score, set_last_score

async def check_live(app):
    matches = fetch_matches("LIVE")
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    for match in matches:
        match_id = match.get("id")
        if not match_id:
            continue

        home_name = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
        away_name = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")

        # Faqat top klublar ishtirok etadigan o'yinlar
        if not (is_top_club(home_name) or is_top_club(away_name)):
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
                detail = fetch_match_detail(match_id)
                if detail:
                    scorer, assist = last_goal_scorer_assist(detail)

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

    matches = fetch_today_matches()
    scheduled = [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]
    if not scheduled:
        return

    lines = [daily_fixtures_header()]
    for m in scheduled:
        lines.append(format_fixture(m))
    text = with_footer("\n\n".join(lines))

    try:
        await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
    except Exception:
        pass

async def post_daily_results_and_standings(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    finished = fetch_today_matches(status="FINISHED")
    if finished:
        lines = [daily_results_header()]
        for m in finished:
            lines.append(format_match(m))
        text = with_footer("\n\n".join(lines))
        try:
            await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        except Exception:
            pass

    for code in ALL_COMPETITIONS:
        table = fetch_standings(code)
        if not table:
            continue
        name = COMPETITION_NAMES.get(code, code)
        caption = standings_caption(name, table)
        try:
            image_path = make_standings_graphic(name, table, filename=f"standings_{code}.png")
            with open(image_path, "rb") as photo:
                await app.bot.send_photo(
                    chat_id=channel, photo=photo, caption=caption, parse_mode="HTML"
                )
        except Exception:
            try:
                await app.bot.send_message(chat_id=channel, text=caption, parse_mode="HTML")
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
        post_daily_fixtures, "cron", hour=7, minute=0, args=[app],
        id="daily_fixtures", replace_existing=True
    )
    scheduler.add_job(
        post_daily_results_and_standings, "cron", hour=23, minute=30, args=[app],
        id="daily_results_standings", replace_existing=True
    )

    scheduler.start()
