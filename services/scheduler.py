import os
import logging
from html import escape
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.football_api import (
    fetch_today_matches, fetch_recent_matches, is_top_club,
    today_uz_date_label,
)
from services import api_football
from services.formatter import (
    daily_fixtures_header, with_footer, news_caption,
)
from services.graphics import make_match_result_graphic
from services.keyboards import channel_main_keyboard
from services.news import get_fresh_news, get_fresh_transfer
from database.db import init_db, was_posted, mark_posted

log = logging.getLogger(__name__)
_API_CACHE = {"at": 0.0, "matches": []}


def _all_today_matches():
    # Big-5 + UCL: football-data.org, polled every minute for near-immediate final results.
    matches = fetch_recent_matches()

    # Cups/MLS/Uzbekistan: one global API-Football request every 30 minutes.
    # This keeps the 100-request/day free quota safe while still catching Top-12 cup finals.
    import time
    now = time.time()
    if now - _API_CACHE["at"] >= 1800:
        try:
            _API_CACHE["matches"] = api_football.fetch_top12_matches_today()
        except AttributeError:
            _API_CACHE["matches"] = []
        _API_CACHE["at"] = now

    matches += _API_CACHE["matches"]
    unique = {}
    for m in matches:
        if m.get("id") is not None:
            unique[str(m["id"])] = m
    return list(unique.values())


async def post_finished_top12(app):
    """Post exactly one result for each finished match involving a Top-12 club.

    No goal-by-goal posts are generated anymore. The result is published as soon
    as the API reports the match as FINISHED.
    """
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return

    for match in _all_today_matches():
        if match.get("status") != "FINISHED":
            continue
        home = (match.get("homeTeam") or {}).get("name", "")
        away = (match.get("awayTeam") or {}).get("name", "")
        if not (is_top_club(home) or is_top_club(away)):
            continue

        match_id = str(match.get("id"))
        key = f"top12:final:{match_id}"
        if was_posted(key):
            continue

        # Fetch scorers/assists and preserve team logos for the graphic.
        if match_id.startswith("af_"):
            match = api_football.enrich_finished_match(match)
        else:
            from services.football_api import enrich_finished_match
            match = enrich_finished_match(match)

        try:
            image_path = make_match_result_graphic(match)
            competition = (match.get("competition") or {}).get("name", "Futbol")
            caption_lines = [f"🏁 <b>{escape(home)} — {(match.get('score') or {}).get('fullTime', {}).get('home', 0)} : {(match.get('score') or {}).get('fullTime', {}).get('away', 0)} — {escape(away)}</b>", f"🏆 {escape(competition)}"]
            events = match.get("events") or []
            scorers = [e for e in events if e.get("scorer")]
            if scorers:
                caption_lines.append("")
                for e in scorers[:8]:
                    minute = f"{e.get('minute')}' " if e.get("minute") else ""
                    assist = f" · 🎯 {e.get('assist')}" if e.get("assist") else ""
                    caption_lines.append(f"⚽ {minute}{escape(str(e.get('scorer')))}{escape(assist)}")
            caption = with_footer("\n".join(caption_lines))
            with open(image_path, "rb") as photo:
                await app.bot.send_photo(
                    chat_id=channel,
                    photo=photo,
                    caption=caption[:1024],
                    parse_mode="HTML",
                )
            mark_posted(key)
        except Exception:
            log.exception("Top-12 final result post failed for %s", match_id)


async def post_daily_fixtures(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return
    matches = [m for m in _all_today_matches() if m.get("status") in {"SCHEDULED", "TIMED"}]
    if not matches:
        return
    header = daily_fixtures_header(today_uz_date_label())
    from services.football_api import group_and_format_fixtures
    text = with_footer(f"{header}\n{group_and_format_fixtures(matches)}")
    key = f"daily_fixtures:{today_uz_date_label()}"
    if was_posted(key):
        return
    try:
        await app.bot.send_message(
            chat_id=channel,
            text=text,
            parse_mode="HTML",
            reply_markup=channel_main_keyboard(),
        )
        mark_posted(key)
    except Exception:
        log.exception("Daily fixtures post failed")


async def post_news(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return
    item = get_fresh_news(was_posted)
    if not item:
        return
    try:
        text = news_caption(item["title"], item["body"] or "Yangilik tafsilotlari manba orqali.", item["source"])
        await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        mark_posted(item["event_key"])
    except Exception:
        log.exception("News post failed")


async def post_transfer(app):
    channel = os.getenv("CHANNEL_ID")
    if not channel:
        return
    item = get_fresh_transfer(was_posted)
    if not item:
        return
    try:
        text = news_caption("🔄 " + item["title"], item["body"] or "Transfer yangiligi.", item["source"])
        await app.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        mark_posted(item["event_key"])
    except Exception:
        log.exception("Transfer post failed")


async def setup_scheduler(app):
    init_db()
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))

    # The old goal-by-goal publisher is deliberately removed.
    scheduler.add_job(post_finished_top12, "interval", minutes=1, args=[app], id="top12_results", replace_existing=True)
    scheduler.add_job(post_daily_fixtures, "cron", hour=8, minute=0, args=[app], id="daily_fixtures", replace_existing=True)

    # 2–3 fresh editorial items per day. Feed URLs can be overridden in .env.
    for i, hour in enumerate((10, 15, 20), start=1):
        scheduler.add_job(post_news, "cron", hour=hour, minute=10, args=[app], id=f"news_{i}", replace_existing=True)
        scheduler.add_job(post_transfer, "cron", hour=hour, minute=40, args=[app], id=f"transfer_{i}", replace_existing=True)

    scheduler.start()
    log.info("Scheduler started: Top-12 finals every minute; fixtures 08:00; news/transfers 3x/day.")
