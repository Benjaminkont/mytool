"""Cache successful translations in a local SQLite database."""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "mytool" / "trans.db"


def init_db() -> None:
    """初始化数据库"""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(DB_PATH)
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    command TEXT PRIMARY KEY,
                    original_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
        finally:
            db.close()
    except (OSError, sqlite3.Error) as error:
        raise RuntimeError(f"无法初始化翻译缓存：{error}") from error


def lookup(cmd : str, text: str) -> str | None:
    """查询是往期是否已经被翻译过"""
    init_db()
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            row_1 = db.execute(
                "SELECT translated_text FROM translations WHERE command = ?",
                (cmd, ),
            ).fetchone()

            row_2 = db.execute(
                "SELECT translated_text FROM translations WHERE  original_text= ?",
                (text, ),
            ).fetchone()
        finally:
            db.close()
    except sqlite3.Error as error:
        raise RuntimeError(f"无法读取翻译缓存：{error}") from error

    if row_1 is not None:
        return row_1[0]
    elif row_2 is not None:
        return row_2[0]
    else:
        return None


def save(cmd : str, text: str, translation: str) -> None:
    """重置往期的翻译结果"""
    init_db()
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            db.execute("""
                INSERT INTO translations (command, original_text, translated_text)
                VALUES (?, ?, ?)
                ON CONFLICT(command) DO UPDATE SET
                    translated_text = excluded.translated_text,
                    updated_at = CURRENT_TIMESTAMP
            """, (cmd, text, translation))
            db.commit()
        finally:
            db.close()
    except sqlite3.Error as error:
        raise RuntimeError(f"无法保存翻译缓存：{error}") from error
