"""SQLite 저장소 (PRD 3단계). 로그인 없는 단일 프로필 + 저장 레시피."""
import app.env  # noqa: F401  (RECIPE_DB를 .env에서도 읽을 수 있도록 가장 먼저 로드)

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("RECIPE_DB", Path(__file__).resolve().parent.parent / "data" / "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nickname TEXT NOT NULL,
    prefs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    data_json TEXT NOT NULL,
    ingredients_json TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
"""

_initialized: Path | None = None  # 스키마를 만든 DB 경로. 프로세스당 1회만 초기화한다.


def init_db() -> None:
    global _initialized
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    _initialized = DB_PATH


@contextmanager
def connect():
    if _initialized != DB_PATH:  # 서버는 시작 시 init_db()를 호출한다. 직접 import 한 경우의 안전장치.
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
