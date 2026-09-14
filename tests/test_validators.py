"""Unit-тесты проверки ввода: имя, телефон, время."""

import unittest

from leadbot.validators import normalize_name, normalize_phone, normalize_time_text


class NameTests(unittest.TestCase):
    def test_plain_names(self) -> None:
        self.assertEqual(normalize_name("Анна"), "Анна")
        self.assertEqual(normalize_name("  Иван   Петров "), "Иван Петров")

    def test_rejects_garbage(self) -> None:
        self.assertIsNone(normalize_name(""))
        self.assertIsNone(normalize_name("   "))
        self.assertIsNone(normalize_name("И"))
        self.assertIsNone(normalize_name("Иван123"))
        self.assertIsNone(normalize_name("123"))


class PhoneTests(unittest.TestCase):
    def test_formats_common_variants(self) -> None:
        self.assertEqual(normalize_phone("+7 999 123-45-67"), "+7 (999) 123-45-67")
        self.assertEqual(normalize_phone("89991234567"), "+7 (999) 123-45-67")
        self.assertEqual(normalize_phone("79991234567"), "+7 (999) 123-45-67")
        self.assertEqual(normalize_phone("999 123 45 67"), "+7 (999) 123-45-67")
        self.assertEqual(normalize_phone("+79991234567"), "+7 (999) 123-45-67")

    def test_contact_phone_passthrough(self) -> None:
        # Telegram присылает Е.164: 11 цифр с кодом страны.
        self.assertEqual(normalize_phone("+79991234567"), "+7 (999) 123-45-67")

    def test_rejects_garbage(self) -> None:
        self.assertIsNone(normalize_phone(""))
        self.assertIsNone(normalize_phone("позвоните мне"))
        self.assertIsNone(normalize_phone("123"))
        self.assertIsNone(normalize_phone("8 999"))
        self.assertIsNone(normalize_phone("***"))


class TimeTests(unittest.TestCase):
    def test_accepts_free_text(self) -> None:
        self.assertEqual(normalize_time_text("завтра после 18:00"), "завтра после 18:00")
        self.assertEqual(normalize_time_text("  сегодня "), "сегодня")

    def test_rejects_garbage(self) -> None:
        self.assertIsNone(normalize_time_text(""))
        self.assertIsNone(normalize_time_text("   "))
        self.assertIsNone(normalize_time_text("5"))
        self.assertIsNone(normalize_time_text("!!! ??"))
        self.assertIsNone(normalize_time_text("—"))


if __name__ == "__main__":
    unittest.main()
