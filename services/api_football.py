"""API-Football (api-sports.io) integratsiyasi.

football-data.org bepul rejasi milliy kubok o'yinlarini (FA Cup, Copa del Rey va h.k.)
va MLS kabi ligalarni bermaydi. Shu bo'shliqni to'ldirish uchun API-Football'ning
bepul rejasidan (100 so'rov/kun) foydalanamiz.

Muhim: bu servis fixture'larni football_api.py bilan bir xil "umumiy shakl"ga
o'giradi (id, utcDate, status, competition, homeTeam, awayTeam, score), shunda
scheduler.py ikkala manbani aralashtirib bitta ro'yxat sifatida ishlata oladi.
"""
import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE_URL = "https://v3.football.api-sports.io"
UZ_TZ = ZoneInfo("Asia/Tashkent")

# football-data.org bepul rejasida yo'q, shuning uchun shu yerdan olinadigan musobaqalar.
# (country, nomi, qisqa kod)
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

# To'liq mavsumli ligalar (kubok emas) — kelajakda standings qo'shish mumkin bo'lgan ro'yxat.
LEAGUES = [MLS, UZBEKISTAN_SUPER_LEAGUE]

ALL_API_FOOTBALL_COMPETITIONS = DOMESTIC_CUPS + LEAGUES

_league_id_cache = {}


def _headers():
    key = os.getenv("API_FOOTBALL_KEY")
    return {"x-apisports-key": key} if key else {}


def _find_league_id(country, name):
    """Musobaqa nomi/mamlakati bo'yicha API-Football league id'sini topadi va keshlaydi.

    Id'larni qo'lda yozib qo'yish xavfli (API vaqti-vaqti bilan o'zgartiradi),
    shuning uchun /leagues endpoint orqali dinamik qidiramiz.
    """
    cache_key = (country, name)
    if cache_key in _league_id_cache:
        return _league_id_cache[cache_key]
    if not os.getenv("API_FOOTBALL_KEY"):
        return None
    try:
        r = requests.get(
            f"{BASE_URL}/leagues",
            headers=_headers(),
            params={"country": country, "search": name},
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("response", [])
    except requests.RequestException:
        return None

    league_id = None
    for item in results:
        league = item.get("league", {})
        if league.get("name", "").strip().lower() == name.strip().lower():
            league_id = league.get("id")
            break
    if league_id is None and results:
        league_id = results[0].get("league", {}).get("id")

    if league_id is not None:
        _league_id_cache[cache_key] = league_id
    return league_id


def _to_utc_z(date_str):
    """API-Football '...+00:00' formatini football_api.py kutgan '...Z' formatiga o'giradi."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str)
        dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return date_str


_STATUS_MAP = {
    "NS": "SCHEDULED", "TBD": "SCHEDULED", "PST": "POSTPONED", "CANC": "POSTPONED",
    "ABD": "POSTPONED", "SUSP": "POSTPONED",
    "1H": "LIVE", "2H": "LIVE", "ET": "LIVE", "P": "LIVE", "LIVE": "LIVE", "BT": "LIVE",
    "HT": "PAUSED",
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
}


def _to_common_shape(fixture_json, competition_name, competition_code):
    fixture = fixture_json.get("fixture", {})
    teams = fixture_json.get("teams", {})
    goals = fixture_json.get("goals", {})
    home = teams.get("home", {}).get("name", "Home")
    away = teams.get("away", {}).get("name", "Away")
    status_short = fixture.get("status", {}).get("short", "")

    return {
        "id": f"af_{fixture.get('id')}",
        "utcDate": _to_utc_z(fixture.get("date", "")),
        "status": _STATUS_MAP.get(status_short, "SCHEDULED"),
        "competition": {"code": competition_code, "name": competition_name},
        "homeTeam": {"name": home, "shortName": home},
        "awayTeam": {"name": away, "shortName": away},
        "score": {"fullTime": {"home": goals.get("home"), "away": goals.get("away")}},
    }


def _fetch_fixtures_for_league(league_id, date_str=None, live=False):
    if not os.getenv("API_FOOTBALL_KEY") or not league_id:
        return []
    params = {"league": league_id}
    if live:
        params["live"] = "all"
    elif date_str:
        params["date"] = date_str
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("response", [])
    except requests.RequestException:
        return []


def fetch_today_matches(include_mls=True, include_uzbekistan=True):
    """Bugungi (Toshkent kuni) kubok/MLS/O'zbekiston Superligasi o'yinlarini umumiy shaklda qaytaradi."""
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    today = datetime.now(timezone.utc).astimezone(UZ_TZ).date().isoformat()
    competitions = list(DOMESTIC_CUPS)
    if include_mls:
        competitions.append(MLS)
    if include_uzbekistan:
        competitions.append(UZBEKISTAN_SUPER_LEAGUE)

    matches = []
    for country, name, code in competitions:
        league_id = _find_league_id(country, name)
        for fx in _fetch_fixtures_for_league(league_id, date_str=today):
            matches.append(_to_common_shape(fx, name, code))
    return matches


def fetch_live_matches(include_mls=True, include_uzbekistan=True):
    """Hozir jonli ketayotgan kubok/MLS/O'zbekiston Superligasi o'yinlarini qaytaradi (gol tekshiruvi uchun)."""
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    competitions = list(DOMESTIC_CUPS)
    if include_mls:
        competitions.append(MLS)
    if include_uzbekistan:
        competitions.append(UZBEKISTAN_SUPER_LEAGUE)

    matches = []
    for country, name, code in competitions:
        league_id = _find_league_id(country, name)
        for fx in _fetch_fixtures_for_league(league_id, live=True):
            matches.append(_to_common_shape(fx, name, code))
    return matches



def fetch_match_detail(match_id):
    """API-Football fixture detailini olib, gol muallifi va assistini qaytaradi."""
    if not os.getenv("API_FOOTBALL_KEY") or not match_id:
        return None
    raw_id = str(match_id)
    if raw_id.startswith("af_"):
        raw_id = raw_id[3:]
    try:
        r = requests.get(
            f"{BASE_URL}/fixtures", headers=_headers(),
            params={"id": raw_id}, timeout=15
        )
        r.raise_for_status()
        response = r.json().get("response", [])
        if response:
            return response[0]
    except requests.RequestException:
        pass
    return None

def goal_scorer_for_score(match_detail, home_score, away_score, previous_home=None, previous_away=None):
    """Hisob o'zgarishiga mos aynan yangi gol muallifi va assistini topadi."""
    if not match_detail:
        return None, None
    fixture_id = (match_detail.get("fixture") or {}).get("id")
    if not fixture_id:
        return None, None
    try:
        r = requests.get(
            f"{BASE_URL}/fixtures/events", headers=_headers(),
            params={"fixture": fixture_id}, timeout=15
        )
        r.raise_for_status()
        events = r.json().get("response", [])
        goals = [e for e in events if e.get("type") == "Goal"]
        if not goals:
            return None, None

        target_home = int(home_score or 0)
        target_away = int(away_score or 0)
        prev_home = int(previous_home or 0)
        prev_away = int(previous_away or 0)
        home_scored = max(0, target_home - prev_home)
        away_scored = max(0, target_away - prev_away)

        home_id = ((match_detail.get("teams") or {}).get("home") or {}).get("id")
        away_id = ((match_detail.get("teams") or {}).get("away") or {}).get("id")

        # Own goal ham hisobni o'zgartiradi, shuning uchun uni chiqarib tashlamaymiz.
        # Team ID orqali aynan hisobni oshirgan jamoaning oxirgi golini olamiz.
        if home_scored > 0 and away_scored == 0 and home_id:
            same_team = [e for e in goals if ((e.get("team") or {}).get("id") == home_id)]
            last = same_team[-1] if same_team else goals[-1]
        elif away_scored > 0 and home_scored == 0 and away_id:
            same_team = [e for e in goals if ((e.get("team") or {}).get("id") == away_id)]
            last = same_team[-1] if same_team else goals[-1]
        else:
            last = goals[-1]

        scorer = (last.get("player") or {}).get("name")
        assist = (last.get("assist") or {}).get("name")
        return scorer, assist
    except (requests.RequestException, TypeError, ValueError):
        return None, None


def last_goal_scorer_assist(match_detail):
    """Backward-compatible helper."""
    return goal_scorer_for_score(match_detail, 0, 0, 0, 0)

def fetch_standings(country, name):
    """API-Football'dan tanlangan liga uchun joriy mavsum jadvalini oladi."""
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    league_id = _find_league_id(country, name)
    if not league_id:
        return []

    current_year = datetime.now(timezone.utc).year
    for season in (current_year, current_year - 1):
        try:
            r = requests.get(
                f"{BASE_URL}/standings",
                headers=_headers(),
                params={"league": league_id, "season": season},
                timeout=15,
            )
            r.raise_for_status()
            response = r.json().get("response", [])
            if not response:
                continue

            # API-Football odatda response[0]["league"]["standings"] = [[...]]
            standings_groups = response[0].get("league", {}).get("standings", [])
            if standings_groups:
                rows = []
                for row in standings_groups[0]:
                    team = row.get("team", {})
                    all_stats = row.get("all", {})
                    rows.append({
                        "position": row.get("rank"),
                        "team": {
                            "name": team.get("name", ""),
                            "shortName": team.get("name", ""),
                        },
                        "points": row.get("points"),
                        "playedGames": all_stats.get("played"),
                    })
                return rows
        except requests.RequestException:
            continue
    return []
