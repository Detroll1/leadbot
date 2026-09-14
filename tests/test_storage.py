"""Unit-тесты хранилища заявок (SQLite, без реального Telegram).

Запуск из корня проекта:  python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from leadbot.storage import LeadStorage


class LeadStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        # Специально несуществующая подпапка: хранилище должно создать её само.
        self.db_path = Path(self._tmp.name) / "data" / "leads.db"
        self.storage = LeadStorage(self.db_path)

    def tearDown(self) -> None:
        self.storage.close()
        self._tmp.cleanup()

    def _add(self, **overrides) -> int:
        params = {
            "user_id": 111,
            "username": "anna",
            "service": "Стрижка и укладка",
            "client_name": "Анна",
            "phone": "+7 (999) 123-45-67",
            "preferred_time": "завтра после 18:00",
        }
        params.update(overrides)
        return self.storage.add(**params)

    def test_add_returns_increasing_ids(self) -> None:
        first = self._add()
        second = self._add(username="ivan", client_name="Иван")
        self.assertLess(first, second)

    def test_recent_returns_latest_first_with_all_fields(self) -> None:
        self._add()
        self._add(username="ivan", client_name="Иван", service="Окрашивание")
        leads = self.storage.recent()
        self.assertEqual(len(leads), 2)
        latest = leads[0]
        self.assertEqual(latest["client_name"], "Иван")
        self.assertEqual(latest["service"], "Окрашивание")
        self.assertEqual(latest["username"], "ivan")
        self.assertEqual(latest["user_id"], 111)
        self.assertEqual(latest["phone"], "+7 (999) 123-45-67")
        self.assertEqual(latest["preferred_time"], "завтра после 18:00")
        datetime.fromisoformat(latest["created_at"])  # дата в валидном ISO

    def test_recent_respects_limit(self) -> None:
        for _ in range(3):
            self._add()
        self.assertEqual(len(self.storage.recent(limit=2)), 2)
        self.assertEqual(len(self.storage.recent(limit=10)), 3)

    def test_count_and_count_since(self) -> None:
        self._add()
        self._add()
        self.assertEqual(self.storage.count(), 2)
        self.assertEqual(self.storage.count_since("2000-01-01T00:00:00"), 2)
        self.assertEqual(self.storage.count_since(datetime.max.isoformat()), 0)

    def test_persistence_after_reopen(self) -> None:
        self._add()
        self._add(username="ivan", client_name="Иван")
        self.storage.close()
        reopened = LeadStorage(self.db_path)
        try:
            self.assertEqual(reopened.count(), 2)
            self.assertEqual(reopened.recent(1)[0]["username"], "ivan")
            reopened.add(user_id=222, username="olga", service="Массаж",
                         client_name="Ольга", phone="89991234567", preferred_time="сегодня")
            self.assertEqual(reopened.count(), 3)
        finally:
            reopened.close()

    def test_username_optional_and_cyrillic(self) -> None:
        self._add(username="", service="Косметология")
        lead = self.storage.recent(1)[0]
        self.assertEqual(lead["username"], "")
        self.assertEqual(lead["service"], "Косметология")

    def test_empty_database(self) -> None:
        self.assertEqual(self.storage.recent(), [])
        self.assertEqual(self.storage.count(), 0)


if __name__ == "__main__":
    unittest.main()
