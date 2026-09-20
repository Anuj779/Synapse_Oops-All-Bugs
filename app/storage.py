"""Small SQLite audit log shared by the API and Streamlit service layer."""
from datetime import datetime, timezone
import json
import sqlite3
from app.config import ARTIFACT_DIR


def record(kind, payload, path=None):
    path = path or ARTIFACT_DIR / 'fleet.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)')
        cursor = conn.execute('INSERT INTO history (created_at, kind, payload) VALUES (?, ?, ?)',
                              (datetime.now(timezone.utc).isoformat(), kind, json.dumps(payload)))
        return cursor.lastrowid


def recent(limit=20, path=None):
    path = path or ARTIFACT_DIR / 'fleet.sqlite3'
    if not path.exists():
        return []
    with sqlite3.connect(path, timeout=5) as conn:
        return [dict(id=row[0], created_at=row[1], kind=row[2]) for row in conn.execute(
            'SELECT id, created_at, kind FROM history ORDER BY id DESC LIMIT ?', (max(1, min(limit, 100)),))]
