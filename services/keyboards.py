from telegram import InlineKeyboardButton, InlineKeyboardMarkup

LEAGUE_BUTTONS = [
    ("🇬🇧 Premier League", "PL"),
    ("🇪🇸 La Liga", "PD"),
    ("🇮🇹 Serie A", "SA"),
    ("🇩🇪 Bundesliga", "BL1"),
    ("🇫🇷 Ligue 1", "FL1"),
    ("🇺🇸 MLS", "MLS"),
    ("🇺🇿 O‘zbekiston Super League", "UZS"),
]
RESULT_BUTTONS = LEAGUE_BUTTONS + [("🏆 UEFA Champions League", "CL")]


def channel_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Fixtures & Results", callback_data="fx_menu")],
        [InlineKeyboardButton("📊 Standings", callback_data="standings_menu")],
    ])


def fixtures_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Fixtures", callback_data="fx:fixtures")],
        [InlineKeyboardButton("🏁 Results", callback_data="fx:results")],
        [InlineKeyboardButton("📊 Standings", callback_data="standings_menu")],
        [InlineKeyboardButton("❌ Yopish", callback_data="fx:close")],
    ])


def league_keyboard(prefix, items):
    rows = [[InlineKeyboardButton(name, callback_data=f"{prefix}:{code}")] for name, code in items]
    rows.append([InlineKeyboardButton("❌ Yopish", callback_data=f"{prefix}_close")])
    return InlineKeyboardMarkup(rows)
