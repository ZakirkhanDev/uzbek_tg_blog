import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "football_bot.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_events (
            event_key TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_type TEXT,
            external_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS match_scores (
            match_id TEXT PRIMARY KEY,
            home INTEGER,
            away INTEGER
        )
        """)
        conn.commit()

def was_posted(event_key: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_events WHERE event_key = ?",
            (event_key,)
        ).fetchone()
        return row is not None

def mark_posted(event_key: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_events(event_key) VALUES (?)",
            (event_key,)
        )
        conn.commit()

def get_last_score(match_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT home, away FROM match_scores WHERE match_id = ?",
            (str(match_id),)
        ).fetchone()
        return row

def set_last_score(match_id, home, away):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO match_scores(match_id, home, away) VALUES (?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET home=excluded.home, away=excluded.away
            """,
            (str(match_id), home, away)
        )
        conn.commit()
