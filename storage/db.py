import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published TEXT,
            fetched_at TEXT,
            category TEXT,
            companies TEXT,
            summary TEXT,
            title_key TEXT
        )
    """)
    conn.commit()
    return conn


def normalize_title(title: str) -> str:
    t = (title or "").lower().strip()
    # cheap normalization
    for ch in ["’", "'", "\"", "“", "”", ":", ";", ",", ".", "!", "?", "(", ")", "[", "]"]:
        t = t.replace(ch, "")
    t = " ".join(t.split())
    return t[:200]