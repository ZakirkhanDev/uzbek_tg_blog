from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import re

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")[:80] or "match"


def _download_image(url, filename):
    if not url:
        return None
    path = ASSETS / filename
    try:
        if path.exists() and path.stat().st_size > 500:
            return path
        r = requests.get(url, timeout=15, headers={"User-Agent": "OtabekZokirovFootballBot/4.0"})
        r.raise_for_status()
        path.write_bytes(r.content)
        return path
    except requests.RequestException:
        return None


def _paste_logo(base, logo_url, box):
    path = _download_image(logo_url, f"logo_{_safe_filename(logo_url)}.png")
    if not path:
        return False
    try:
        logo = Image.open(path).convert("RGBA")
        logo.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
        x = box[0] + ((box[2] - box[0]) - logo.width) // 2
        y = box[1] + ((box[3] - box[1]) - logo.height) // 2
        base.paste(logo, (x, y), logo)
        return True
    except Exception:
        return False


def make_match_result_graphic(match, filename=None):
    """Original editorial match-result graphic inspired by modern football media layouts.

    It does not scrape or copy 433/Instagram artwork. It uses the match's own team logos
    when available and generates a fresh branded composition for Otabek Zokirov Blogi.
    """
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), (17, 17, 17))
    draw = ImageDraw.Draw(img)

    # Subtle vertical bands / editorial background.
    draw.rectangle((0, 0, width, 210), fill=(9, 9, 9))
    draw.rectangle((0, 1120, width, height), fill=(9, 9, 9))

    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    home_name = home.get("shortName") or home.get("name") or "Home"
    away_name = away.get("shortName") or away.get("name") or "Away"
    score = match.get("score", {}).get("fullTime", {})
    hs = 0 if score.get("home") is None else score.get("home")
    aws = 0 if score.get("away") is None else score.get("away")
    comp = (match.get("competition") or {}).get("name") or "Football"

    # Brand mark.
    draw.text((55, 48), "OZB", font=_font(38, True), fill="white")
    draw.text((55, 100), "OTABEK ZOKIROV BLOGI", font=_font(27, True), fill=(205, 205, 205))
    draw.text((width - 55, 58), "FINAL", font=_font(34, True), fill="white", anchor="ra")

    # Competition line.
    draw.text((width // 2, 260), comp.upper(), font=_font(34, True), fill=(210, 210, 210), anchor="mm")
    draw.text((width // 2, 315), "FULL TIME", font=_font(26), fill=(145, 145, 145), anchor="mm")

    # Logos.
    _paste_logo(img, home.get("crest") or home.get("logo"), (120, 380, 430, 690))
    _paste_logo(img, away.get("crest") or away.get("logo"), (650, 380, 960, 690))

    # Team names.
    draw.text((275, 735), str(home_name), font=_font(42, True), fill="white", anchor="mm")
    draw.text((805, 735), str(away_name), font=_font(42, True), fill="white", anchor="mm")

    # Score.
    draw.text((540, 560), f"{hs}", font=_font(122, True), fill="white", anchor="rm")
    draw.text((540, 560), " - ", font=_font(88, True), fill=(170, 170, 170), anchor="mm")
    draw.text((540, 560), f"{aws}", font=_font(122, True), fill="white", anchor="lm")

    # Separator.
    draw.line((90, 825, width - 90, 825), fill=(75, 75, 75), width=2)

    # Optional scorer summary from API if present.
    events = match.get("events") or []
    if events:
        y = 875
        draw.text((90, y), "GOALS", font=_font(27, True), fill=(175, 175, 175))
        y += 55
        for event in events[:6]:
            side = "" if event.get("side") == "home" else ""
            minute = event.get("minute")
            scorer = event.get("scorer") or ""
            if not scorer:
                continue
            label = f"{minute}'  {scorer}" if minute else scorer
            draw.text((90, y), label, font=_font(30), fill="white")
            y += 45
            if y > 1080:
                break

    draw.text((55, height - 75), "@otabekzokirov1", font=_font(29, True), fill="white")
    draw.text((width - 55, height - 75), "FT", font=_font(29, True), fill=(180, 180, 180), anchor="ra")

    output = ASSETS / (filename or f"result_{_safe_filename(home_name)}_{_safe_filename(away_name)}.jpg")
    img.save(output, quality=94, optimize=True)
    return output


def make_standings_graphic(competition_name, table, filename="standings.png", limit=10):
    rows = table[:limit]
    row_h, header_h, col_h, footer_h = 78, 190, 60, 70
    width = 1080
    height = header_h + col_h + row_h * len(rows) + footer_h
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, header_h), fill="black")
    draw.text((60, 45), "TURNIR JADVALI", font=_font(46, True), fill="white")
    draw.text((60, 110), competition_name, font=_font(56, True), fill="white")
    col_y = header_h + 10
    draw.text((60, col_y), "#", font=_font(30, True), fill="black")
    draw.text((140, col_y), "JAMOA", font=_font(30, True), fill="black")
    draw.text((700, col_y), "O'YIN", font=_font(30, True), fill="black")
    draw.text((830, col_y), "FARQ", font=_font(30, True), fill="black")
    draw.text((950, col_y), "OCHKO", font=_font(30, True), fill="black")
    draw.line((60, col_y + 45, width - 60, col_y + 45), fill="black", width=3)
    y = header_h + col_h
    for i, row in enumerate(rows):
        team = row.get("team", {}).get("shortName") or row.get("team", {}).get("name", "")
        played = row.get("playedGames")
        points = row.get("points")
        gd = row.get("goalDifference")
        gd_str = f"+{gd}" if isinstance(gd, int) and gd > 0 else str(gd)
        if i % 2 == 0:
            draw.rectangle((0, y, width, y + row_h), fill=(240, 240, 240))
        draw.text((60, y + 18), str(row.get("position")), font=_font(38, True), fill="black")
        team_display = str(team) if len(str(team)) <= 22 else str(team)[:21] + "…"
        draw.text((140, y + 18), team_display, font=_font(38), fill="black")
        draw.text((700, y + 18), str(played), font=_font(38), fill="black")
        draw.text((830, y + 18), gd_str, font=_font(38), fill="black")
        draw.text((950, y + 18), str(points), font=_font(38, True), fill="black")
        y += row_h
    draw.text((60, height - 55), "@otabekzokirov1", font=_font(30, True), fill="black")
    output = ASSETS / filename
    img.save(output)
    return output
