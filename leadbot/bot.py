"""Логика бота: пошаговый сбор заявки и админ-команды.

Собирается функцией build_application() — её вызывает run.py.
"""

import logging
import re
from datetime import datetime

from telegram import BotCommand, BotCommandScopeChat, Update, User
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import keyboards, texts
from .config import Settings
from .storage import LeadStorage
from .validators import normalize_name, normalize_phone, normalize_time_text

log = logging.getLogger(__name__)

CHOOSING_SERVICE, TYPING_NAME, TYPING_PHONE, TYPING_TIME, CONFIRMING = range(5)

_CANCEL_RE = re.compile(r"^\s*(?:❌\s*)?отмена\s*$", re.IGNORECASE)
_SUBMIT_RE = re.compile(r"^\s*(?:✅\s*)?отправить заявку\s*$", re.IGNORECASE)
_RESTART_RE = re.compile(r"^\s*(?:🔁\s*)?заполнить заново\s*$", re.IGNORECASE)
_ORDER_RE = re.compile(r"оставить заявку", re.IGNORECASE)
_INFO_RE = re.compile(r"^\s*(?:ℹ️\s*)?о\s+демо\s*$", re.IGNORECASE)
# Bot API не пускает кириллицу в зарегистрированные команды, поэтому /заявки и
# /статус ловим точным регэкспом по тексту (латинские /leads и /stats — обычные команды).
_LEADS_RE = re.compile(r"^\s*/заявки(?:@\S+)?\s*$", re.IGNORECASE)
_STATS_RE = re.compile(r"^\s*/статус(?:@\S+)?\s*$", re.IGNORECASE)
_TEXTISH = (filters.TEXT | filters.CONTACT) & ~filters.COMMAND


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Приветствие и главное меню; сбрасывает незавершённую заявку."""
    context.user_data.clear()
    await update.effective_message.reply_text(texts.WELCOME, reply_markup=keyboards.main_menu())
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Кнопка «Отмена» или команда /cancel — назад в главное меню."""
    context.user_data.clear()
    await update.effective_message.reply_text(texts.CANCELLED, reply_markup=keyboards.main_menu())
    return ConversationHandler.END


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(texts.INFO_ABOUT, reply_markup=keyboards.main_menu())


async def menu_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Любой вольный текст вне диалога — мягко возвращаем к кнопкам."""
    await update.effective_message.reply_text(texts.MENU_HINT, reply_markup=keyboards.main_menu())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(texts.UNKNOWN_COMMAND)


async def ask_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    settings: Settings = context.bot_data["settings"]
    await update.effective_message.reply_text(
        texts.ASK_SERVICE, reply_markup=keyboards.services_kb(settings.services)
    )
    return CHOOSING_SERVICE


async def got_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["lead"] = {"service": update.effective_message.text.strip()}
    await update.effective_message.reply_text(texts.ASK_NAME, reply_markup=keyboards.name_kb())
    return TYPING_NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = normalize_name(update.effective_message.text or "")
    if name is None:
        await update.effective_message.reply_text(texts.ERR_NAME)
        return TYPING_NAME
    context.user_data.setdefault("lead", {})["name"] = name
    await update.effective_message.reply_text(texts.ASK_PHONE, reply_markup=keyboards.phone_kb())
    return TYPING_PHONE


async def got_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _save_phone(update, context, update.effective_message.contact.phone_number or "")


async def got_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _save_phone(update, context, update.effective_message.text or "")


async def _save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str) -> int:
    phone = normalize_phone(raw)
    if phone is None:
        await update.effective_message.reply_text(texts.ERR_PHONE)
        return TYPING_PHONE
    context.user_data.setdefault("lead", {})["phone"] = phone
    await update.effective_message.reply_text(texts.ASK_TIME, reply_markup=keyboards.time_kb())
    return TYPING_TIME


async def got_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    when = normalize_time_text(update.effective_message.text or "")
    if when is None:
        await update.effective_message.reply_text(texts.ERR_TIME)
        return TYPING_TIME
    context.user_data.setdefault("lead", {})["time"] = when
    summary = texts.CONFIRM_TEMPLATE.format(**context.user_data["lead"])
    await update.effective_message.reply_text(summary, reply_markup=keyboards.confirm_kb())
    return CONFIRMING


async def confirm_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    return await ask_service(update, context)


async def confirm_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(texts.CONFIRM_HINT)
    return CONFIRMING


async def confirm_submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lead = context.user_data.get("lead") or {}
    if not all(key in lead for key in ("service", "name", "phone", "time")):
        return await ask_service(update, context)

    storage: LeadStorage = context.bot_data["storage"]
    settings: Settings = context.bot_data["settings"]
    user = update.effective_user
    lead_id = storage.add(
        user_id=user.id,
        username=user.username or "",
        service=lead["service"],
        client_name=lead["name"],
        phone=lead["phone"],
        preferred_time=lead["time"],
    )
    await _notify_admin(context, settings, lead, lead_id, user)
    context.user_data.clear()
    await update.effective_message.reply_text(
        texts.SENT_OK.format(id=lead_id), reply_markup=keyboards.main_menu()
    )
    log.info("Заявка №%d сохранена (клиент id %s)", lead_id, user.id)
    return ConversationHandler.END


async def _notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    settings: Settings,
    lead: dict,
    lead_id: int,
    user: User,
) -> None:
    if settings.admin_id is None:
        log.warning("ADMIN_ID не задан — заявка №%d сохранена только в базу", lead_id)
        return
    tg = f"@{user.username} (id {user.id})" if user.username else f"id {user.id}"
    try:
        await context.bot.send_message(
            chat_id=settings.admin_id,
            text=texts.ADMIN_NOTIFY_TEMPLATE.format(id=lead_id, tg=tg, **lead),
        )
    except TelegramError:
        log.exception("Не удалось отправить заявку №%d админу %s", lead_id, settings.admin_id)


async def _admin_gate(update: Update, settings: Settings) -> bool:
    """Проверяет право на админ-команды и сам отвечает при отказе."""
    if settings.admin_id is None:
        await update.effective_message.reply_text(texts.ADMIN_NO_ID)
        return False
    if not update.effective_user or update.effective_user.id != settings.admin_id:
        await update.effective_message.reply_text(texts.ADMIN_DENIED)
        return False
    return True


def _format_lead_row(lead: dict) -> str:
    created = datetime.fromisoformat(lead["created_at"])
    tg = f"@{lead['username']} (id {lead['user_id']})" if lead["username"] else f"id {lead['user_id']}"
    return (
        f"№{lead['id']} · {created:%d.%m %H:%M}\n"
        f"🛎 {lead['service']}\n"
        f"👤 {lead['client_name']}, 📞 {lead['phone']}\n"
        f"🕑 {lead['preferred_time']}\n"
        f"💬 {tg}"
    )


async def admin_list_leads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/заявки — последние N заявок; только для владельца."""
    settings: Settings = context.bot_data["settings"]
    if not await _admin_gate(update, settings):
        return
    storage: LeadStorage = context.bot_data["storage"]
    total = storage.count()
    leads = storage.recent(settings.recent_limit)
    if not leads:
        await update.effective_message.reply_text(texts.ADMIN_EMPTY)
        return
    header = texts.ADMIN_LIST_HEADER.format(shown=len(leads), total=total)
    body = "\n\n".join(_format_lead_row(lead) for lead in leads)
    await update.effective_message.reply_text(header + body)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/статус — сколько заявок всего и за сегодня; только для владельца."""
    settings: Settings = context.bot_data["settings"]
    if not await _admin_gate(update, settings):
        return
    storage: LeadStorage = context.bot_data["storage"]
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(
        timespec="seconds"
    )
    await update.effective_message.reply_text(
        texts.ADMIN_STATS.format(total=storage.count(), today=storage.count_since(today_start))
    )


async def _post_init(application: Application) -> None:
    """Меню команд: клиенту — общие, владельцу — ещё и админские."""
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Главное меню"),
            BotCommand("cancel", "Отменить заполнение заявки"),
        ]
    )
    settings: Settings = application.bot_data["settings"]
    if settings.admin_id is not None:
        try:
            await application.bot.set_my_commands(
                [
                    BotCommand("leads", "Последние заявки"),
                    BotCommand("stats", "Статистика заявок"),
                ],
                scope=BotCommandScopeChat(settings.admin_id),
            )
        except TelegramError:
            # Чаще всего владелец ещё не нажал /start у бота — меню для него не критично.
            log.warning("Не удалось задать меню команд для админа %s", settings.admin_id)


def build_application(settings: Settings) -> Application:
    """Собирает приложение: диалог заявки + админ-команды + подсказки."""
    storage = LeadStorage(settings.db_path)

    async def close_storage(application: Application) -> None:
        storage.close()

    app = (
        ApplicationBuilder()
        .token(settings.token)
        .post_init(_post_init)
        .post_shutdown(close_storage)
        .build()
    )
    app.bot_data["settings"] = settings
    app.bot_data["storage"] = storage

    # Админ-команды ставим раньше диалога: работают даже посреди заявки.
    app.add_handler(CommandHandler("leads", admin_list_leads))
    app.add_handler(MessageHandler(filters.Regex(_LEADS_RE), admin_list_leads))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(MessageHandler(filters.Regex(_STATS_RE), admin_stats))

    service_re = re.compile(
        r"^\s*(?:" + "|".join(re.escape(service) for service in settings.services) + r")\s*$",
        re.IGNORECASE,
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex(_ORDER_RE), ask_service),
        ],
        states={
            CHOOSING_SERVICE: [
                MessageHandler(filters.Regex(_CANCEL_RE), cmd_cancel),
                MessageHandler(filters.Regex(service_re), got_service),
                CommandHandler("cancel", cmd_cancel),
                CommandHandler("start", cmd_start),
                MessageHandler(_TEXTISH, ask_service),
            ],
            TYPING_NAME: [
                MessageHandler(filters.Regex(_CANCEL_RE), cmd_cancel),
                CommandHandler("cancel", cmd_cancel),
                CommandHandler("start", cmd_start),
                MessageHandler(_TEXTISH, got_name),
            ],
            TYPING_PHONE: [
                MessageHandler(filters.Regex(_CANCEL_RE), cmd_cancel),
                MessageHandler(filters.CONTACT, got_phone_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_phone_text),
                CommandHandler("cancel", cmd_cancel),
                CommandHandler("start", cmd_start),
            ],
            TYPING_TIME: [
                MessageHandler(filters.Regex(_CANCEL_RE), cmd_cancel),
                CommandHandler("cancel", cmd_cancel),
                CommandHandler("start", cmd_start),
                MessageHandler(_TEXTISH, got_time),
            ],
            CONFIRMING: [
                MessageHandler(filters.Regex(_SUBMIT_RE), confirm_submit),
                MessageHandler(filters.Regex(_RESTART_RE), confirm_restart),
                MessageHandler(filters.Regex(_CANCEL_RE), cmd_cancel),
                CommandHandler("cancel", cmd_cancel),
                CommandHandler("start", cmd_start),
                MessageHandler(_TEXTISH, confirm_hint),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, unknown_command)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex(_INFO_RE), cmd_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_hint))
    return app
