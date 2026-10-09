"""Cache successful translations in a local SQLite database."""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "mytool" / "trans.db"


def init_db() -> None:
    """Create the database and translations table if needed."""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(DB_PATH)
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    original_text TEXT PRIMARY KEY,
                    translated_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
        finally:
            db.close()
    except (OSError, sqlite3.Error) as error:
        raise RuntimeError(f"无法初始化翻译缓存：{error}") from error


def lookup(text: str) -> str | None:
    """Return a translation when the complete input text matches."""
    init_db()
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            row = db.execute(
                "SELECT translated_text FROM translations WHERE original_text = ?",
                (text,),
            ).fetchone()
        finally:
            db.close()
    except sqlite3.Error as error:
        raise RuntimeError(f"无法读取翻译缓存：{error}") from error

    return row[0] if row is not None else None


def save(text: str, translation: str) -> None:
    """Insert or replace the translation for the complete input text."""
    init_db()
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            db.execute("""
                INSERT INTO translations (original_text, translated_text)
                VALUES (?, ?)
                ON CONFLICT(original_text) DO UPDATE SET
                    translated_text = excluded.translated_text,
                    updated_at = CURRENT_TIMESTAMP
            """, (text, translation))
            db.commit()
        finally:
            db.close()
    except sqlite3.Error as error:
        raise RuntimeError(f"无法保存翻译缓存：{error}") from error
