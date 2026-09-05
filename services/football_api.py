import os
import requests
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

BASE_URL = "https://api.football-data.org/v4"

# Big 5 ligalar
LEAGUES = ["PL", "PD", "SA", "BL1", "FL1"]

# Kubok/turnirlar (football-data.org bepul reja doirasida)
CUPS = ["CL", "WC", "EC"]

# Kunlik fixtures/natijalar uchun barcha musobaqalar
ALL_COMPETITIONS = LEAGUES + CUPS

COMPETITION_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "WC": "Jahon chempionati",
    "EC": "Yevropa chempionati",
}

UZ_TZ = ZoneInfo("Asia/Tashkent")
HOUSTON_TZ = ZoneInfo("America/Chicago")  # Houston, TX (CDT/CST)

def dual_time(utc_date_str):
    """utcDate ('2026-06-15T18:00:00Z') dan UZ va Houston (TX) vaqtini qaytaradi."""
    if not utc_date_str:
        return "?", "?"
    try:
        dt = datetime.strptime(utc_date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
        uz = dt.astimezone(UZ_TZ).strftime("%H:%M")
        us = dt.astimezone(HOUSTON_TZ).strftime("%H:%M")
        return uz, us
    except ValueError:
        return "?", "?"

TOP_CLUBS = {
    "real madrid", "barcelona", "manchester city", "man city",
    "manchester united", "man utd", "liverpool", "arsenal", "chelsea",
    "bayern münchen", "bayern munich", "fc bayern münchen",
    "paris saint-germain", "psg", "juventus", "inter", "internazionale",
    "ac milan", "milan", "basaksehir",
}

def is_top_club(name):
    if not name:
        return False
    n = name.strip().lower()
    return any(club in n for club in TOP_CLUBS)

def _headers():
    key = os.getenv("FOOTBALL_API_KEY")
    return {"X-Auth-Token": key} if key else {}

def fetch_matches(status="LIVE"):
    if not os.getenv("FOOTBALL_API_KEY"):
        return []
    try:
        r = requests.get(
            f"{BASE_URL}/matches",
            headers=_headers(),
            params={"status": status, "competitions": ",".join(ALL_COMPETITIONS)},
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("matches", [])
    except requests.RequestException:
        return []

def fetch_today_matches(status=None):
    if not os.getenv("FOOTBALL_API_KEY"):
        return []
    today = datetime.now(timezone.utc).astimezone(UZ_TZ).date().isoformat()
    params = {
        "competitions": ",".join(ALL_COMPETITIONS),
        "dateFrom": today,
        "dateTo": today,
    }
    if status:
        params["status"] = status
    try:
        r = requests.get(
            f"{BASE_URL}/matches",
            headers=_headers(),
            params=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("matches", [])
    except requests.RequestException:
        return []

def fetch_match_detail(match_id):
    """Bitta o'yin haqida to'liq ma'lumot (gol muallifi/assist uchun)."""
    if not os.getenv("FOOTBALL_API_KEY"):
        return None
    try:
        r = requests.get(
            f"{BASE_URL}/matches/{match_id}",
            headers=_headers(),
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None

def last_goal_scorer_assist(match_detail):
    """Match detailidagi 'goals' ro'yxatidan oxirgi golning muallifi va assistini qaytaradi."""
    if not match_detail:
        return None, None
    goals = match_detail.get("goals") or []
    if not goals:
        return None, None
    last = goals[-1]
    scorer = (last.get("scorer") or {}).get("name")
    assist = (last.get("assist") or {}).get("name")
    return scorer, assist

def fetch_standings(competition_code):
    if not os.getenv("FOOTBALL_API_KEY"):
        return []
    try:
        r = requests.get(
            f"{BASE_URL}/competitions/{competition_code}/standings",
            headers=_headers(),
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        for group in data.get("standings", []):
            if group.get("type") == "TOTAL":
                return group.get("table", [])
        return []
    except requests.RequestException:
        return []

def format_match(match):
    home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")

    score = match.get("score", {})
    full = score.get("fullTime", {})
    h = full.get("home")
    a = full.get("away")
    h = 0 if h is None else h
    a = 0 if a is None else a

    code = match.get("competition", {}).get("code", "")
    competition = COMPETITION_NAMES.get(code) or match.get("competition", {}).get("name", "Futbol")
    status = match.get("status", "UNKNOWN")

    status_map = {
        "LIVE": "🔴 JONLI",
        "IN_PLAY": "🔴 JONLI",
        "PAUSED": "⏸ TANAFFUS",
        "FINISHED": "🏁 YAKUNLANDI",
        "POSTPONED": "⏸ QOLDIRILDI",
        "SCHEDULED": "🕒 REJALASHTIRILGAN",
        "TIMED": "🕒 REJALASHTIRILGAN",
    }

    return (
        f"⚽ <b>{competition}</b>\n\n"
        f"{home}  <b>{h} : {a}</b>  {away}\n"
        f"{status_map.get(status, status)}"
    )

def format_fixture(match):
    home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")
    code = match.get("competition", {}).get("code", "")
    competition = COMPETITION_NAMES.get(code) or match.get("competition", {}).get("name", "Futbol")
    uz_time, us_time = dual_time(match.get("utcDate", ""))
    return (
        f"🏆 <i>{competition}</i>\n"
        f"⚽ <b>{home}</b> — <b>{away}</b>\n"
        f"🇺🇿 {uz_time} (Toshkent)   |   🇺🇸 {us_time} (Houston)"
    )
