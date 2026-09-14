"""Кнопки бота: главное меню и клавиатуры каждого шага заявки."""

from telegram import KeyboardButton, ReplyKeyboardMarkup

ORDER_LABEL = "🛎 Оставить заявку"
INFO_LABEL = "ℹ️ О демо"
CANCEL_LABEL = "❌ Отмена"
SUBMIT_LABEL = "✅ Отправить заявку"
RESTART_LABEL = "🔁 Заполнить заново"
SEND_CONTACT_LABEL = "📱 Отправить мой номер"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ORDER_LABEL)], [KeyboardButton(INFO_LABEL)]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def services_kb(services: tuple[str, ...]) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(service) for service in services[i : i + 2]]
        for i in range(0, len(services), 2)
    ]
    rows.append([KeyboardButton(CANCEL_LABEL)])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите услугу",
    )


def name_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(CANCEL_LABEL)]],
        resize_keyboard=True,
        input_field_placeholder="Напишите имя",
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(SEND_CONTACT_LABEL, request_contact=True)], [KeyboardButton(CANCEL_LABEL)]],
        resize_keyboard=True,
        input_field_placeholder="Или напишите номер сообщением",
    )


def time_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(CANCEL_LABEL)]],
        resize_keyboard=True,
        input_field_placeholder="Например: завтра после 18:00",
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(SUBMIT_LABEL)],
            [KeyboardButton(RESTART_LABEL)],
            [KeyboardButton(CANCEL_LABEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
