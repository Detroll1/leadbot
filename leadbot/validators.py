"""Проверка ввода клиента: имя, телефон, удобное время. Пустое и бред не принимаем."""

import re

_PHONE_CHARS = re.compile(r"[0-9+()\-\s]+")
_NON_DIGITS = re.compile(r"\D")
_ANY_LETTER_OR_DIGIT = re.compile(r"[0-9a-zа-яё]", re.IGNORECASE)
_ANY_DIGIT = re.compile(r"\d")

_MAX_INPUT_LENGTH = 120


def normalize_name(raw: str) -> str | None:
    """Чистит имя: схлопывает пробелы, отбрасывает цифры и слишком короткие строки."""
    name = re.sub(r"\s+", " ", (raw or "")).strip()
    if len(name) < 2 or len(name) > _MAX_INPUT_LENGTH:
        return None
    if _ANY_DIGIT.search(name):
        return None
    return name


def normalize_phone(raw: str) -> str | None:
    """Приводит телефон к виду +7 (999) 123-45-67, если похоже на номер."""
    text = (raw or "").strip()
    if not text or not _PHONE_CHARS.fullmatch(text):
        return None
    digits = _NON_DIGITS.sub("", text)
    if len(digits) == 11 and digits[0] in "78":
        d = "7" + digits[1:]
        return f"+7 ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}"
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    if 11 <= len(digits) <= 15:
        return ("+" + digits) if text.startswith("+") else digits
    return None


def normalize_time_text(raw: str) -> str | None:
    """Время — свободный текст («завтра после 18:00»), но не пустышка из знаков."""
    text = re.sub(r"\s+", " ", (raw or "")).strip()
    if len(text) < 2 or len(text) > _MAX_INPUT_LENGTH:
        return None
    if not _ANY_LETTER_OR_DIGIT.search(text):
        return None
    return text
