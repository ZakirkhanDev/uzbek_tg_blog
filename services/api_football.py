"""API-Football fallback for MLS, Uzbekistan and domestic cups.

The main European leagues + UCL come from football-data.org. API-Football fills
competitions that are unavailable there on the user's plan.
"""
import os
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BASE_URL = "https://v3.football.api-sports.io"
UZ_TZ = ZoneInfo("Asia/Tashkent")

DOMESTIC_CUPS = [
    ("England", "FA Cup", "FAC"),
    ("England", "EFL Cup", "ELC2"),
    ("Spain", "Copa del Rey", "CDR"),
    ("Italy", "Coppa Italia", "CIT"),
    ("Germany", "DFB Pokal", "DFB"),
    ("France", "Coupe de France", "CDF"),
]
MLS = ("USA", "MLS", "MLS")
UZBEKISTAN_SUPER_LEAGUE = ("Uzbekistan", "Super League", "UZS")

_league_id_cache = {}
# Stable API-Football league IDs for the competitions this bot uses.
# Dynamic lookup remains as a fallback for standings.
KNOWN_LEAGUE_IDS = {
    "FAC": 45, "ELC2": 48, "CDR": 143, "CIT": 137,
    "DFB": 81, "CDF": 66, "MLS": 253, "UZS": 278,
}
TOP12_API_CODES = {"FAC", "ELC2", "CDR", "CIT", "DFB", "CDF"}


def _headers():
    key = os.getenv("API_FOOTBALL_KEY")
    return {"x-apisports-key": key} if key else {}


def _get(path, params=None):
    if not os.getenv("API_FOOTBALL_KEY"):
        return None
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params or {}, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def _find_league_id(country, name):
    key = (country, name)
    if key in _league_id_cache:
        return _league_id_cache[key]
    data = _get("/leagues", {"country": country, "search": name})
    results = (data or {}).get("response", [])
    wanted = name.strip().lower()
    league_id = None
    for item in results:
        league = item.get("league", {})
        if league.get("name", "").strip().lower() == wanted:
            league_id = league.get("id")
            break
    if league_id is None and results:
        league_id = results[0].get("league", {}).get("id")
    if league_id:
        _league_id_cache[key] = league_id
    return league_id


def _to_utc_z(date_str):
    if not date_str:
        return ""
    try:
        return datetime.fromisoformat(date_str).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return date_str


_STATUS_MAP = {
    "NS": "SCHEDULED", "TBD": "SCHEDULED", "PST": "POSTPONED", "CANC": "POSTPONED",
    "ABD": "POSTPONED", "SUSP": "POSTPONED", "1H": "LIVE", "2H": "LIVE",
    "ET": "LIVE", "P": "LIVE", "LIVE": "LIVE", "BT": "LIVE", "HT": "PAUSED",
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
}


def _to_common_shape(raw, competition_name, competition_code):
    fixture = raw.get("fixture", {})
    teams = raw.get("teams", {})
    goals = raw.get("goals", {})
    home = teams.get("home", {})
    away = teams.get("away", {})
    short = fixture.get("status", {}).get("short", "")
    return {
        "id": f"af_{fixture.get('id')}",
        "utcDate": _to_utc_z(fixture.get("date", "")),
        "status": _STATUS_MAP.get(short, "SCHEDULED"),
        "competition": {"code": competition_code, "name": competition_name},
        "homeTeam": {"name": home.get("name", "Home"), "shortName": home.get("name", "Home"), "crest": home.get("logo")},
        "awayTeam": {"name": away.get("name", "Away"), "shortName": away.get("name", "Away"), "crest": away.get("logo")},
        "score": {"fullTime": {"home": goals.get("home"), "away": goals.get("away")}},
        "apiFootballId": fixture.get("id"),
    }


def _today_uz():
    now = datetime.now(timezone.utc).astimezone(UZ_TZ)
    return now.date()


def _fetch_for_league(league_id, date_str=None, live=False):
    if not league_id:
        return []
    params = {"league": league_id}
    if live:
        params["live"] = "all"
    elif date_str:
        params["date"] = date_str
    data = _get("/fixtures", params)
    return (data or {}).get("response", [])


def fetch_today_matches(include_mls=True, include_uzbekistan=True):
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    day = _today_uz()
    competitions = list(DOMESTIC_CUPS)
    if include_mls:
        competitions.append(MLS)
    if include_uzbekistan:
        competitions.append(UZBEKISTAN_SUPER_LEAGUE)
    out = []
    for country, name, code in competitions:
        league_id = _find_league_id(country, name)
        for raw in _fetch_for_league(league_id, day.isoformat()):
            m = _to_common_shape(raw, name, code)
            try:
                dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone(UZ_TZ)
                if dt.date() == day:
                    out.append(m)
            except (ValueError, TypeError):
                continue
    return out


def fetch_recent_matches(include_mls=True, include_uzbekistan=True):
    """Yesterday + today in Uzbekistan time, useful for matches ending after midnight."""
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    day = _today_uz()
    days = [day - timedelta(days=1), day]
    competitions = list(DOMESTIC_CUPS)
    if include_mls:
        competitions.append(MLS)
    if include_uzbekistan:
        competitions.append(UZBEKISTAN_SUPER_LEAGUE)
    out = []
    for country, name, code in competitions:
        league_id = _find_league_id(country, name)
        for d in days:
            for raw in _fetch_for_league(league_id, d.isoformat()):
                m = _to_common_shape(raw, name, code)
                try:
                    dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone(UZ_TZ)
                    if dt.date() in days:
                        out.append(m)
                except (ValueError, TypeError):
                    continue
    return out


def fetch_top12_matches_today():
    """One API-Football request for today's cup/MLS/Uzbekistan fixtures.

    Used by the result scheduler only every 30 minutes, keeping the 100/day API quota safe.
    """
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    day = _today_uz().isoformat()
    data = _get("/fixtures", {"date": day, "timezone": "Asia/Tashkent"})
    response = (data or {}).get("response", [])
    wanted = set(KNOWN_LEAGUE_IDS.values())
    out = []
    for raw in response:
        league_id = (raw.get("league") or {}).get("id")
        if league_id not in wanted:
            continue
        league = raw.get("league") or {}
        code = next((c for c, i in KNOWN_LEAGUE_IDS.items() if i == league_id), "")
        out.append(_to_common_shape(raw, league.get("name", code), code))
    return out


def fetch_live_matches(include_mls=True, include_uzbekistan=True):
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    competitions = list(DOMESTIC_CUPS)
    if include_mls:
        competitions.append(MLS)
    if include_uzbekistan:
        competitions.append(UZBEKISTAN_SUPER_LEAGUE)
    out = []
    for country, name, code in competitions:
        league_id = _find_league_id(country, name)
        for raw in _fetch_for_league(league_id, live=True):
            out.append(_to_common_shape(raw, name, code))
    return out


def fetch_match_detail(match_id):
    raw_id = str(match_id or "")
    if raw_id.startswith("af_"):
        raw_id = raw_id[3:]
    data = _get("/fixtures", {"id": raw_id})
    response = (data or {}).get("response", [])
    return response[0] if response else None


def enrich_finished_match(match):
    detail = fetch_match_detail(match.get("id"))
    if not detail:
        return match
    events_data = _get("/fixtures/events", {"fixture": (detail.get("fixture") or {}).get("id")})
    events = []
    for e in (events_data or {}).get("response", []):
        if e.get("type") != "Goal":
            continue
        player = (e.get("player") or {}).get("name")
        if not player:
            continue
        minute = (e.get("time") or {}).get("elapsed")
        extra = (e.get("time") or {}).get("extra")
        minute_label = f"{minute}+{extra}" if minute and extra else minute
        events.append({
            "minute": minute_label,
            "scorer": player,
            "assist": (e.get("assist") or {}).get("name"),
            "team": (e.get("team") or {}).get("name"),
        })
    result = dict(match)
    result["events"] = events
    return result


def goal_scorer_for_score(match_detail, home_score, away_score, previous_home=None, previous_away=None):
    # Kept for compatibility with older code.
    if not match_detail:
        return None, None
    fixture_id = (match_detail.get("fixture") or {}).get("id")
    data = _get("/fixtures/events", {"fixture": fixture_id}) if fixture_id else None
    goals = [e for e in (data or {}).get("response", []) if e.get("type") == "Goal"]
    if not goals:
        return None, None
    last = goals[-1]
    return (last.get("player") or {}).get("name"), (last.get("assist") or {}).get("name")


def fetch_standings(country, name):
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    league_id = _find_league_id(country, name)
    if not league_id:
        return []
    current_year = datetime.now(timezone.utc).year
    for season in (current_year, current_year - 1):
        data = _get("/standings", {"league": league_id, "season": season})
        response = (data or {}).get("response", [])
        if not response:
            continue
        groups = response[0].get("league", {}).get("standings", [])
        if not groups:
            continue
        rows = []
        for row in groups[0]:
            team = row.get("team", {})
            all_stats = row.get("all", {})
            rows.append({
                "position": row.get("rank"),
                "team": {"name": team.get("name", ""), "shortName": team.get("name", ""), "crest": team.get("logo")},
                "points": row.get("points"),
                "playedGames": all_stats.get("played"),
                "goalDifference": row.get("goalsDiff"),
            })
        return rows
    return []
