"""Хранилище заявок: один файл SQLite рядом с ботом, без внешних сервисов."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT    NOT NULL,
    user_id        INTEGER NOT NULL,
    username       TEXT    NOT NULL DEFAULT '',
    service        TEXT    NOT NULL,
    client_name    TEXT    NOT NULL,
    phone          TEXT    NOT NULL,
    preferred_time TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at);
"""


class LeadStorage:
    """Добавление и чтение заявок. Потокобезопасен в пределах одного процесса."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def add(
        self,
        *,
        user_id: int,
        username: str,
        service: str,
        client_name: str,
        phone: str,
        preferred_time: str,
    ) -> int:
        """Сохраняет заявку и возвращает её номер."""
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO leads"
                " (created_at, user_id, username, service, client_name, phone, preferred_time)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    created_at,
                    int(user_id),
                    username or "",
                    service,
                    client_name,
                    phone,
                    preferred_time,
                ),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def recent(self, limit: int = 10) -> list[dict]:
        """Последние заявки: свежие сверху."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, created_at, user_id, username, service,"
                " client_name, phone, preferred_time"
                " FROM leads ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        """Всего заявок в базе."""
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0])

    def count_since(self, since_iso: str) -> int:
        """Заявок начиная с указанного момента (строка ISO, например начало дня)."""
        with self._lock:
            return int(
                self._conn.execute(
                    "SELECT COUNT(*) FROM leads WHERE created_at >= ?",
                    (since_iso,),
                ).fetchone()[0]
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
