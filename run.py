"""Точка входа leadbot: `python run.py` поднимает поллинг.

Токен берётся из TELEGRAM_BOT_TOKEN (окружение / .env / config.py) — см. leadbot.config.
Все ошибки запуска (нет токена, токен отклонён, второй экземпляр, сеть)
показываются понятной строкой вместо трейсбека.
"""

import asyncio
import logging
import sys

from telegram.error import Conflict, InvalidToken, NetworkError
from telegram.ext import Application

from leadbot.bot import build_application
from leadbot.config import get_settings

TOKEN_HOWTO = (
    "Не задан токен бота (TELEGRAM_BOT_TOKEN).\n\n"
    "Как исправить — любой из способов:\n"
    "  1. Переменная окружения:\n"
    "       PowerShell:  $env:TELEGRAM_BOT_TOKEN=\"1234567890:AA...\"\n"
    "       CMD:         set TELEGRAM_BOT_TOKEN=1234567890:AA...\n"
    "  2. Файл .env в корне проекта (образец — .env.example).\n"
    "  3. Файл config.py в корне проекта (образец — config.example.py).\n\n"
    "Токен выдаёт @BotFather в Telegram: /newbot → имя бота → токен."
)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def _start(app: Application) -> None:
    """Инициализация, проверка токена и проба на конфликт поллинга."""
    await app.initialize()
    if app.post_init is not None:
        await app.post_init(app)
    me = await app.bot.get_me()
    # Проба getUpdates: если этот токен уже поллится другим процессом,
    # конфликт ловим здесь и уходим с понятным сообщением, а не в цикле ошибок.
    await app.bot.get_updates(limit=1, timeout=1, allowed_updates=["message"])
    await app.start()
    await app.updater.start_polling(allowed_updates=["message"])
    print(f"✅ Бот @{me.username} запущен и ждёт сообщений: https://t.me/{me.username}")
    print("Остановка — Ctrl+C")


async def _stop(app: Application) -> None:
    if app.updater and app.updater.running:
        await app.updater.stop()
    if app.running:
        await app.stop()
    await app.shutdown()


def main() -> int:
    _setup_logging()
    try:
        settings = get_settings()
    except Exception as exc:  # сломанный config.py и т.п.
        print(f"Не удалось прочитать настройки: {exc}")
        return 1

    if not settings.token:
        print(TOKEN_HOWTO)
        return 1
    if "вставьте" in settings.token.lower() or "ваш_токен" in settings.token.lower():
        print("В TELEGRAM_BOT_TOKEN остался пример-заглушка — впишите настоящий токен от @BotFather.")
        return 1
    if ":" not in settings.token:
        print(
            "Токен не похож на токен Telegram: должно быть двоеточие, "
            "например 1234567890:AA... Токен выдаёт @BotFather."
        )
        return 1
    if settings.admin_id is None:
        print(
            "⚠️ ADMIN_ID не задан: заявки будут сохраняться в базу, "
            "но не будут приходить в личку. Как узнать свой ID — в README."
        )

    app = build_application(settings)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_start(app))
        loop.run_forever()
    except InvalidToken:
        print("⛔ Telegram отклонил токен (ошибка 401). Проверьте TELEGRAM_BOT_TOKEN: токен из @BotFather, целиком, без пробелов.")
        return 1
    except Conflict:
        print("⛔ Конфликт поллинга: этот бот уже запущен другим процессом. Остановите второй экземпляр и запустите снова.")
        return 1
    except NetworkError:
        print("⛔ Нет связи с api.telegram.org. Проверьте интернет/VPN и запустите снова.")
        return 1
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as exc:
        logging.exception("Непредвиденная ошибка при запуске")
        print(f"⛔ Непредвиденная ошибка: {exc}")
        return 1
    finally:
        try:
            loop.run_until_complete(_stop(app))
        except Exception:
            pass
        loop.close()
    print("Бот остановлен.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
