# Otabek Zokirov Blogi — Professional Football Media Bot V4

## Final behavior
- **No goal-by-goal channel spam.** Live goals are not automatically posted.
- **Top 12 automatic final results:** when a match involving one of the 12 featured clubs is reported as FINISHED, the bot posts exactly one original result graphic.
- Featured clubs: Real Madrid, Barcelona, PSG, Liverpool, Manchester City, Arsenal, Bayern Munich, AC Milan, Inter, Manchester United, Atlético Madrid, Juventus.
- Final-result graphics use available team crests and an original editorial layout inspired by modern football media. The bot does **not** scrape/copy 433 or Instagram artwork.
- **Daily fixtures at 08:00 Asia/Tashkent**, with channel buttons for Fixtures & Results and Standings.
- **News and transfers 3x/day** using configurable RSS feeds; SQLite prevents duplicate stories.
- Fixtures/Results and Standings callbacks work from both `/start` and channel posts.
- Uzbekistan time is 24-hour. USA time uses 12-hour format such as `1 pm CDT`.
- Footer: `@otabekzokirov1`.

## Commands
- `/start` — bot menu
- `/holat` — status
- `/natija` — live scores on demand (not auto-posted)
- `/post Text` — admin manual post
- `/transfer Player | Old club | New club | Details | Source` — admin manual transfer
- `/xabar Title | Body | Source` — admin manual news
- `/test_jadval` — send today's fixture post now
- `/test_natija` — immediately check Top-12 final results

## Setup
1. Create venv: `python3 -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Set Telegram token, channel, admin ID, and API keys.
6. Run: `python3 bot.py`

Never publish `.env` or API keys.

## API quota note
The main result loop uses football-data.org for the five major leagues + UCL. API-Football is only queried periodically for cup/MLS/Uzbekistan fallback data, rather than once per league every minute.
