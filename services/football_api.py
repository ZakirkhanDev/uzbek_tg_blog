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
    "real madrid",
    "barcelona",
    "paris saint-germain", "psg",
    "liverpool",
    "manchester city", "man city",
    "arsenal",
    "bayern münchen", "bayern munich", "fc bayern münchen",
    "ac milan", "milan",
    "inter", "internazionale", "inter milan",
    "manchester united", "man utd",
    "atletico madrid", "atlético madrid",
}

def is_top_club(name):
    if not name:
        return False
    n = name.strip().lower()
    return any(club in n for club in TOP_CLUBS)

# O'zbekiston Superligasidan jonli-gol xabarnomasi kerak bo'lgan klublar
UZ_TOP_CLUBS = {"navbahor", "pakhtakor", "neftchi", "nasaf"}

def is_uz_top_club(name):
    if not name:
        return False
    n = name.strip().lower()
    return any(club in n for club in UZ_TOP_CLUBS)

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

def goal_scorer_for_score(match_detail, home_score, away_score, previous_home=None, previous_away=None):
    """Yangi hisobga mos aynan gol muallifini topadi.

    Oddiy last-goal yondashuvi o'rniga hisobdagi o'zgarishni hisobga oladi.
    Shu sabab 2:1 ga chiqqanida oldingi gol emas, aynan 2:1 ni qilgan futbolchi olinadi.
    """
    if not match_detail:
        return None, None
    goals = match_detail.get("goals") or []
    if not goals:
        return None, None

    try:
        target_home = int(home_score or 0)
        target_away = int(away_score or 0)
        prev_home = int(previous_home or 0)
        prev_away = int(previous_away or 0)
    except (TypeError, ValueError):
        return None, None

    home_scored = max(0, target_home - prev_home)
    away_scored = max(0, target_away - prev_away)

    # API qaytargan goal ro'yxati odatda vaqt tartibida bo'ladi.
    # Hisob o'zgarishiga mos jamoaning eng oxirgi golini tanlaymiz.
    normal_goals = [g for g in goals if g.get("type") != "Own Goal"]
    candidates = normal_goals or goals

    def team_name(goal):
        return ((goal.get("team") or {}).get("name") or "").strip().lower()

    home_name = ((match_detail.get("homeTeam") or {}).get("name") or "").strip().lower()
    away_name = ((match_detail.get("awayTeam") or {}).get("name") or "").strip().lower()

    if home_scored > 0 and away_scored == 0:
        team_goals = [g for g in candidates if team_name(g) == home_name] if home_name else []
        if team_goals:
            last = team_goals[-1]
        else:
            last = candidates[-1]
    elif away_scored > 0 and home_scored == 0:
        team_goals = [g for g in candidates if team_name(g) == away_name] if away_name else []
        if team_goals:
            last = team_goals[-1]
        else:
            last = candidates[-1]
    else:
        last = candidates[-1]

    scorer = (last.get("scorer") or {}).get("name")
    assist = (last.get("assist") or {}).get("name")
    return scorer, assist


def last_goal_scorer_assist(match_detail):
    """Backward-compatible helper: oxirgi gol muallifi va assistini qaytaradi."""
    if not match_detail:
        return None, None
    goals = match_detail.get("goals") or []
    if not goals:
        return None, None
    last = goals[-1]
    return (last.get("scorer") or {}).get("name"), (last.get("assist") or {}).get("name")

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
        f"🇺🇿 {uz_time}   |   🇺🇸 {us_time} CDT"
    )

UZ_MONTHS = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentabr", 10: "oktabr", 11: "noyabr", 12: "dekabr",
}

def today_uz_date_label():
    """Bugungi sanani '6-sentabr' ko'rinishida qaytaradi (Toshkent vaqti bo'yicha)."""
    d = datetime.now(timezone.utc).astimezone(UZ_TZ).date()
    return f"{d.day}-{UZ_MONTHS[d.month]}"

def group_and_format_fixtures(matches):
    """Kunlik o'yinlarni musobaqa bo'yicha guruhlab, har biriga UZ/US (CDT) vaqtini qo'shib matn qiladi."""
    groups = {}
    for m in matches:
        code = m.get("competition", {}).get("code", "")
        name = COMPETITION_NAMES.get(code) or m.get("competition", {}).get("name", "Futbol")
        groups.setdefault(name, []).append(m)

    # Avval bilgan (PL/PD/SA/BL1/FL1/CL/WC/EC) ligalar tartibi bo'yicha, keyin
    # boshqa manbadan kelgan (kubok, MLS) guruhlar nomi bo'yicha alifbo tartibida
    ordered_names = []
    for code in ALL_COMPETITIONS:
        name = COMPETITION_NAMES.get(code, code)
        if name in groups and name not in ordered_names:
            ordered_names.append(name)
    for name in sorted(groups.keys()):
        if name not in ordered_names:
            ordered_names.append(name)

    blocks = []
    for name in ordered_names:
        ms = sorted(groups[name], key=lambda m: m.get("utcDate", ""))
        lines = [f"🏆 <b>{name}</b>"]
        for m in ms:
            home = m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", "Home")
            away = m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", "Away")
            uz_time, us_time = dual_time(m.get("utcDate", ""))
            lines.append(f"🇺🇿 {uz_time}  |  🇺🇸 {us_time} CDT — <b>{home}</b> — <b>{away}</b>")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
