# Otabek Zokirov Football Media Bot — Final V3

Professional Uzbek football Telegram bot.

## Features
- Top 5 European leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- Champions League, World Cup and European Championship competition codes
- Live score polling every minute
- Goal alerts are **text-only** (no image)
- Goal scorer and assist lookup when supplied by the football-data.org match detail
- Uzbekistan and Houston local times for fixtures
- Daily fixtures and results
- Automatic standings graphics generated with Pillow
- Branded footer: `@otabekzokirov1`
- Transfer/news commands with real football photos from Wikimedia Commons
- Star-player caption formatting for admin-uploaded media
- SQLite duplicate/score tracking
- Admin-only posting commands

## Commands
- `/start`
- `/holat`
- `/natija`
- `/post Your text`
- `/transfer Player | Old club | New club | Details | Source`
- `/xabar Title | Body | Source`

## Setup
1. Create a virtual environment: `python3 -m venv venv`
2. Activate it: `source venv/bin/activate`
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`
5. Put your Telegram bot token, channel ID, admin Telegram numeric ID, and football-data.org API key in `.env`.
6. Run: `python3 bot.py`

Never publish your `.env` or bot token.

## Media note
The bot uses Wikimedia Commons' public API for automatic real-photo lookup. It does not scrape Instagram, 433, Flashscore, or other social pages.
