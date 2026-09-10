import os
import requests
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

BASE_URL = "https://api.football-data.org/v4"

LEAGUES = ["PL", "PD", "SA", "BL1", "FL1"]
CUPS = ["CL", "WC", "EC"]
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
HOUSTON_TZ = ZoneInfo("America/Chicago")
UTC = timezone.utc

# Exact 12 clubs used for automatic final-result posts.
TOP_CLUBS = {
    "real madrid", "real madrid cf",
    "barcelona", "fc barcelona",
    "paris saint-germain", "paris saint germain", "psg",
    "liverpool", "liverpool fc",
    "manchester city", "man city", "manchester city fc",
    "arsenal", "arsenal fc",
    "bayern münchen", "bayern munich", "fc bayern münchen", "fc bayern munich",
    "ac milan", "milan", "ac milan spa",
    "inter", "internazionale", "inter milan", "fc internazionale milano",
    "manchester united", "man utd", "manchester united fc",
    "atletico madrid", "atlético madrid", "club atletico de madrid",
    "juventus", "juventus fc",
}


def normalize_team_name(name):
    return " ".join((name or "").strip().lower().replace("’", "'").split())


def is_top_club(name):
    n = normalize_team_name(name)
    if not n:
        return False
    return n in TOP_CLUBS or any(alias in n for alias in TOP_CLUBS if len(alias) > 5)


def _headers():
    key = os.getenv("FOOTBALL_API_KEY")
    return {"X-Auth-Token": key} if key else {}


def _uz_date_utc_window(day):
    start_utc = datetime.combine(day, time.min, tzinfo=UZ_TZ).astimezone(UTC)
    end_utc = datetime.combine(day + timedelta(days=1), time.min, tzinfo=UZ_TZ).astimezone(UTC)
    return start_utc.date().isoformat(), end_utc.date().isoformat()


def _uz_day_utc_window():
    now_uz = datetime.now(UTC).astimezone(UZ_TZ)
    day = now_uz.date()
    start_date, end_date = _uz_date_utc_window(day)
    return start_date, end_date, day


def dual_time(utc_date_str):
    if not utc_date_str:
        return "?", "?"
    try:
        raw = utc_date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw).astimezone(UTC)
        uz = dt.astimezone(UZ_TZ).strftime("%H:%M")
        us_dt = dt.astimezone(HOUSTON_TZ)
        if us_dt.minute == 0:
            us = us_dt.strftime("%-I %p").lower()
        else:
            us = us_dt.strftime("%-I:%M %p").lower()
        return uz, us
    except (ValueError, TypeError):
        return "?", "?"


def _request(path, params=None):
    if not os.getenv("FOOTBALL_API_KEY"):
        return None
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params or {}, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def fetch_matches(status="LIVE"):
    data = _request("/matches", {"status": status, "competitions": ",".join(ALL_COMPETITIONS)})
    return (data or {}).get("matches", [])


def fetch_today_matches(status=None):
    """Fetch matches belonging to today's Uzbekistan calendar date."""
    _, _, day = _uz_day_utc_window()
    return fetch_matches_for_uz_dates([day], status=status)


def fetch_recent_matches(status=None):
    """Fetch yesterday + today in Uzbekistan time; useful for late finished matches."""
    day = datetime.now(UTC).astimezone(UZ_TZ).date()
    return fetch_matches_for_uz_dates([day - timedelta(days=1), day], status=status)


def fetch_matches_for_uz_dates(days, status=None):
    if not os.getenv("FOOTBALL_API_KEY"):
        return []
    days = sorted(set(days))
    if not days:
        return []
    start_date, _ = _uz_date_utc_window(days[0])
    _, end_date = _uz_date_utc_window(days[-1])
    data = _request("/matches", {
        "competitions": ",".join(ALL_COMPETITIONS),
        "dateFrom": start_date,
        "dateTo": end_date,
    })
    matches = (data or {}).get("matches", [])
    wanted = set(days)
    out = []
    for m in matches:
        raw = m.get("utcDate")
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UZ_TZ)
            if dt.date() not in wanted:
                continue
        except (AttributeError, ValueError):
            continue
        if status and m.get("status") != status:
            continue
        out.append(m)
    return out


def fetch_match_detail(match_id):
    return _request(f"/matches/{match_id}")


def enrich_finished_match(match):
    """Attach compact goal events for a final-result graphic/caption."""
    detail = fetch_match_detail(match.get("id"))
    if not detail:
        return match
    events = []
    for goal in detail.get("goals") or []:
        scorer = (goal.get("scorer") or {}).get("name")
        if not scorer:
            continue
        minute = goal.get("minute")
        extra = goal.get("injuryTime")
        minute_label = f"{minute}+{extra}" if minute and extra else minute
        team = (goal.get("team") or {}).get("name")
        events.append({
            "minute": minute_label,
            "scorer": scorer,
            "assist": (goal.get("assist") or {}).get("name"),
            "team": team,
        })
    match = dict(match)
    match["events"] = events
    return match


def goal_scorer_for_score(match_detail, home_score, away_score, previous_home=None, previous_away=None):
    if not match_detail:
        return None, None
    goals = [g for g in (match_detail.get("goals") or []) if g.get("scorer")]
    if not goals:
        return None, None
    try:
        ph = int(previous_home or 0)
        pa = int(previous_away or 0)
        h = int(home_score or 0)
        a = int(away_score or 0)
    except (TypeError, ValueError):
        return None, None
    home_scored = h > ph
    away_scored = a > pa
    home_name = normalize_team_name((match_detail.get("homeTeam") or {}).get("name"))
    away_name = normalize_team_name((match_detail.get("awayTeam") or {}).get("name"))
    candidates = goals
    if home_scored and not away_scored:
        same = [g for g in candidates if normalize_team_name((g.get("team") or {}).get("name")) == home_name]
        last = same[-1] if same else candidates[-1]
    elif away_scored and not home_scored:
        same = [g for g in candidates if normalize_team_name((g.get("team") or {}).get("name")) == away_name]
        last = same[-1] if same else candidates[-1]
    else:
        last = candidates[-1]
    return (last.get("scorer") or {}).get("name"), (last.get("assist") or {}).get("name")


def fetch_standings(competition_code):
    data = _request(f"/competitions/{competition_code}/standings")
    for group in (data or {}).get("standings", []):
        if group.get("type") == "TOTAL":
            return group.get("table", [])
    return []


def format_match(match):
    home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")
    score = match.get("score", {}).get("fullTime", {})
    h = 0 if score.get("home") is None else score.get("home")
    a = 0 if score.get("away") is None else score.get("away")
    code = match.get("competition", {}).get("code", "")
    competition = COMPETITION_NAMES.get(code) or match.get("competition", {}).get("name", "Futbol")
    status = match.get("status", "UNKNOWN")
    status_map = {
        "LIVE": "🔴 JONLI", "IN_PLAY": "🔴 JONLI", "PAUSED": "⏸ TANAFFUS",
        "FINISHED": "🏁 YAKUNLANDI", "POSTPONED": "⏸ QOLDIRILDI",
        "SCHEDULED": "🕒 REJALASHTIRILGAN", "TIMED": "🕒 REJALASHTIRILGAN",
    }
    return f"⚽ <b>{competition}</b>\n\n{home}  <b>{h} : {a}</b>  {away}\n{status_map.get(status, status)}"


def format_fixture(match):
    home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Away")
    code = match.get("competition", {}).get("code", "")
    competition = COMPETITION_NAMES.get(code) or match.get("competition", {}).get("name", "Futbol")
    uz_time, us_time = dual_time(match.get("utcDate", ""))
    return f"🏆 <i>{competition}</i>\n⚽ <b>{home}</b> — <b>{away}</b>\n🇺🇿 {uz_time}  |  🇺🇸 {us_time} CDT"


UZ_MONTHS = {1:"yanvar",2:"fevral",3:"mart",4:"aprel",5:"may",6:"iyun",7:"iyul",8:"avgust",9:"sentabr",10:"oktabr",11:"noyabr",12:"dekabr"}


def today_uz_date_label():
    d = datetime.now(UTC).astimezone(UZ_TZ).date()
    return f"{d.day}-{UZ_MONTHS[d.month]}"


def group_and_format_fixtures(matches):
    groups = {}
    for m in matches:
        code = m.get("competition", {}).get("code", "")
        name = COMPETITION_NAMES.get(code) or m.get("competition", {}).get("name", "Futbol")
        groups.setdefault(name, []).append(m)
    order = [COMPETITION_NAMES[c] for c in ALL_COMPETITIONS]
    names = [n for n in order if n in groups] + [n for n in sorted(groups) if n not in order]
    blocks = []
    for name in names:
        ms = sorted(groups[name], key=lambda x: x.get("utcDate", ""))
        lines = [f"🏆 <b>{name}</b>"]
        for m in ms:
            home = m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", "Home")
            away = m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", "Away")
            uz, us = dual_time(m.get("utcDate", ""))
            lines.append(f"🇺🇿 {uz}  |  🇺🇸 {us} CDT — <b>{home}</b> — <b>{away}</b>")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
