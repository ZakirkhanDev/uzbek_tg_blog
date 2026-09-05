from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)

def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def make_standings_graphic(competition_name, table, filename="standings.png", limit=10):
    rows = table[:limit]
    row_h = 78
    header_h = 190
    col_h = 60
    footer_h = 70
    width = 1080
    height = header_h + col_h + row_h * len(rows) + footer_h

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Sarlavha
    draw.rectangle((0, 0, width, header_h), fill="black")
    draw.text((60, 45), "TURNIR JADVALI", font=_font(46, True), fill="white")
    draw.text((60, 110), competition_name, font=_font(56, True), fill="white")

    # Ustun sarlavhalari
    col_y = header_h + 10
    draw.text((60, col_y), "#", font=_font(30, True), fill="black")
    draw.text((140, col_y), "JAMOA", font=_font(30, True), fill="black")
    draw.text((700, col_y), "O'YIN", font=_font(30, True), fill="black")
    draw.text((830, col_y), "FARQ", font=_font(30, True), fill="black")
    draw.text((950, col_y), "OCHKO", font=_font(30, True), fill="black")
    draw.line((60, col_y + 45, width - 60, col_y + 45), fill="black", width=3)

    y = header_h + col_h
    for i, row in enumerate(rows):
        pos = row.get("position")
        team = row.get("team", {}).get("shortName") or row.get("team", {}).get("name", "")
        played = row.get("playedGames")
        points = row.get("points")
        gd = row.get("goalDifference")
        gd_str = f"+{gd}" if isinstance(gd, int) and gd > 0 else str(gd)

        if i % 2 == 0:
            draw.rectangle((0, y, width, y + row_h), fill=(240, 240, 240))

        draw.text((60, y + 18), str(pos), font=_font(38, True), fill="black")
        team_display = team if len(str(team)) <= 22 else str(team)[:21] + "…"
        draw.text((140, y + 18), team_display, font=_font(38), fill="black")
        draw.text((700, y + 18), str(played), font=_font(38), fill="black")
        draw.text((830, y + 18), gd_str, font=_font(38), fill="black")
        draw.text((950, y + 18), str(points), font=_font(38, True), fill="black")
        y += row_h

    draw.text((60, height - 55), "@otabekzokirov1", font=_font(30, True), fill="black")

    output = ASSETS / filename
    img.save(output)
    return output

def make_text_graphic(title, subtitle="", filename="post.png"):
    img = Image.new("RGB", (1080, 1080), "white")
    draw = ImageDraw.Draw(img)

    # Original, simple branded layout; colors can be customized later.
    draw.rectangle((0, 0, 1080, 170), fill="black")
    draw.text((60, 55), "UZBEK FOOTBALL", font=_font(58, True), fill="white")

    draw.text((60, 280), title, font=_font(72, True), fill="black")

    y = 410
    for line in textwrap.wrap(subtitle, width=32):
        draw.text((60, y), line, font=_font(42), fill="black")
        y += 65

    draw.text((60, 970), "@otabekzokirov1", font=_font(34, True), fill="black")

    output = ASSETS / filename
    img.save(output)
    return output
