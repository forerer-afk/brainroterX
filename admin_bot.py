import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import urllib.request
import urllib.error
import json


# =====================================================
# НАСТРОЙКИ
# =====================================================

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "").strip()

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "").strip()

ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1273118871"))

FUNCTION_URL = (
    "https://obbxdztisfeutsvljiek.supabase.co/"
    "functions/v1/telegram-player"
)

if not ADMIN_BOT_TOKEN:
    raise RuntimeError(
        "В Railway Variables не найден ADMIN_BOT_TOKEN"
    )

if not ADMIN_SECRET:
    raise RuntimeError(
        "В Railway Variables не найден ADMIN_SECRET"
    )


# =====================================================
# ЗАПРОС К СЕРВЕРУ
# =====================================================

def call_server(action, **kwargs):

    payload = {
        "action": action,
        "admin_secret": ADMIN_SECRET,
        **kwargs,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        FUNCTION_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            text = (
                response
                .read()
                .decode("utf-8")
            )

            return json.loads(text)

    except urllib.error.HTTPError as error:

        try:
            text = (
                error
                .read()
                .decode("utf-8")
            )

            return json.loads(text)

        except Exception:
            return {
                "ok": False,
                "error": f"HTTP ошибка {error.code}"
            }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error)
        }


# =====================================================
# ПРОВЕРКА АДМИНА
# =====================================================

def is_admin(update: Update):

    user = update.effective_user

    if not user:
        return False

    return user.id == ADMIN_TELEGRAM_ID


def is_owner(update: Update):
    return is_admin(update)


def get_promo_access(telegram_id: int):
    return call_server(
        "admin_get_promo_delegate",
        actor_telegram_id=telegram_id,
    )


# =====================================================
# /START
# =====================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    if not user:
        return

    if is_owner(update):
        await update.message.reply_text(
            "🛠 ADMIN BOT\n\n"
        "Создать промокод:\n"
        "/promo КОД АКТИВАЦИИ МОНЕТЫ\n\n"
        "Пример:\n"
        "/promo lavaka676 5 5\n\n"
        "Отключить промокод:\n"
        "/promoff lavaka676\n\n"
        "⛔ Отключить пополнение: /-\n"
        "✅ Включить пополнение: /+\n\n"
        "😈 Включить визуальный prank:\n"
        "/mem+ TELEGRAM_ID\n\n"
        "🙂 Выключить визуальный prank:\n"
        "/mem- TELEGRAM_ID\n\n"
        "🍀 Включить повышенный шанс:\n"
        "/luck+ TELEGRAM_ID\n\n"
        "🍀 Выключить повышенный шанс:\n"
        "/luck- TELEGRAM_ID\n\n"
        "👥 Делегированные промо:\n"
        "/promoadd ID КОЛ-ВО — выдать/добавить лимит\n"
        "/promotake ID КОЛ-ВО — убрать лимит\n"
        "/promoblock ID — полностью забрать доступ\n"
        "/promoinfo ID — посмотреть лимит"
        )
        return

    access = get_promo_access(user.id)
    if not access.get("ok") or not access.get("allowed"):
        await update.message.reply_text("❌ Нет доступа")
        return

    await update.message.reply_text(
        "🎟 ДОСТУП К ПРОМОКОДАМ\n\n"
        "/promo КОД АКТИВАЦИИ МОНЕТЫ\n\n"
        f"Максимум на 1 промо: {access.get('max_uses_per_promo', 15)} активаций\n"
        f"Максимум награда: {access.get('max_reward_coins', 10)} монет\n"
        f"Осталось создать промокодов: {access.get('remaining_promos', 0)}"
    )


# =====================================================
# СОЗДАНИЕ ПРОМОКОДА
# =====================================================

async def promo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    if not user:
        return

    args = context.args

    if len(args) != 3:

        await update.message.reply_text(
            "❌ Неверная команда.\n\n"
            "Используй:\n"
            "/promo КОД АКТИВАЦИИ МОНЕТЫ\n\n"
            "Например:\n"
            "/promo lavaka676 5 5"
        )

        return

    code = args[0].strip()

    try:

        max_uses = int(args[1])

        reward_coins = int(args[2])

    except ValueError:

        await update.message.reply_text(
            "❌ Количество активаций "
            "и награда должны быть числами."
        )

        return

    if max_uses < 1:

        await update.message.reply_text(
            "❌ Активаций должно быть минимум 1."
        )

        return

    if reward_coins < 1:

        await update.message.reply_text(
            "❌ Награда должна быть минимум 1 монета."
        )

        return

    await update.message.reply_text(
        "⏳ Создаю промокод..."
    )

    result = call_server(
        "admin_create_promo",
        actor_telegram_id=user.id,
        actor_username=(user.username or ""),
        actor_name=(user.full_name or ""),
        code=code,
        max_uses=max_uses,
        reward_coins=reward_coins,
    )

    if not result.get("ok"):

        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )

        return

    promo = result.get(
        "promo",
        {}
    )

    await update.message.reply_text(
        "✅ ПРОМОКОД СОЗДАН\n\n"
        f"🎟 Код: {promo.get('code', code)}\n"
        f"👥 Активаций: {promo.get('max_uses', max_uses)}\n"
        f"💰 Награда: {promo.get('reward_coins', reward_coins)} монет"
        + (
            f"\n📦 Осталось создать: {result.get('remaining_promos')}"
            if result.get("remaining_promos") is not None
            else ""
        )
    )


# =====================================================
# ДЕЛЕГИРОВАННЫЕ СОЗДАТЕЛИ ПРОМО
# =====================================================

async def promoadd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Использование:\n/promoadd TELEGRAM_ID КОЛ-ВО")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ID и количество должны быть числами")
        return
    if amount < 1:
        await update.message.reply_text("❌ Количество должно быть минимум 1")
        return
    result = call_server(
        "admin_adjust_promo_delegate",
        actor_telegram_id=ADMIN_TELEGRAM_ID,
        target_telegram_id=target_id,
        delta=amount,
    )
    if not result.get("ok"):
        await update.message.reply_text("❌ " + result.get("error", "Ошибка"))
        return
    await update.message.reply_text(
        f"✅ Доступ выдан/увеличен\n"
        f"🆔 {target_id}\n"
        f"📦 Можно создать промокодов: {result.get('remaining_promos', 0)}\n"
        f"👥 Лимит активаций на 1 промо: {result.get('max_uses_per_promo', 15)}\n"
        f"💰 Лимит награды: {result.get('max_reward_coins', 10)} монет"
    )


async def promotake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Использование:\n/promotake TELEGRAM_ID КОЛ-ВО")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ID и количество должны быть числами")
        return
    if amount < 1:
        await update.message.reply_text("❌ Количество должно быть минимум 1")
        return
    result = call_server(
        "admin_adjust_promo_delegate",
        actor_telegram_id=ADMIN_TELEGRAM_ID,
        target_telegram_id=target_id,
        delta=-amount,
    )
    if not result.get("ok"):
        await update.message.reply_text("❌ " + result.get("error", "Ошибка"))
        return
    await update.message.reply_text(
        f"✅ Лимит уменьшен\n🆔 {target_id}\n"
        f"📦 Осталось: {result.get('remaining_promos', 0)}"
    )


async def promoblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование:\n/promoblock TELEGRAM_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Telegram ID должен быть числом")
        return
    result = call_server(
        "admin_block_promo_delegate",
        actor_telegram_id=ADMIN_TELEGRAM_ID,
        target_telegram_id=target_id,
    )
    if not result.get("ok"):
        await update.message.reply_text("❌ " + result.get("error", "Ошибка"))
        return
    await update.message.reply_text(f"⛔ Доступ к созданию промо забран\n🆔 {target_id}")


async def promoinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование:\n/promoinfo TELEGRAM_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Telegram ID должен быть числом")
        return
    result = call_server(
        "admin_get_promo_delegate",
        actor_telegram_id=target_id,
    )
    if not result.get("ok"):
        await update.message.reply_text("❌ " + result.get("error", "Ошибка"))
        return
    await update.message.reply_text(
        f"👤 PROMO-ДОСТУП\n🆔 {target_id}\n"
        f"✅ Доступ: {'да' if result.get('allowed') else 'нет'}\n"
        f"📦 Осталось промокодов: {result.get('remaining_promos', 0)}\n"
        f"👥 До {result.get('max_uses_per_promo', 15)} активаций\n"
        f"💰 До {result.get('max_reward_coins', 10)} монет"
    )


# =====================================================
# ОТКЛЮЧЕНИЕ ПРОМОКОДА
# =====================================================

async def promoff_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):

        await update.message.reply_text(
            "❌ Нет доступа"
        )

        return

    if len(context.args) != 1:

        await update.message.reply_text(
            "❌ Используй:\n"
            "/promoff КОД\n\n"
            "Например:\n"
            "/promoff lavaka676"
        )

        return

    code = context.args[0].strip()

    await update.message.reply_text(
        "⏳ Отключаю промокод..."
    )

    result = call_server(
        "admin_disable_promo",
        code=code,
    )

    if not result.get("ok"):

        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )

        return

    await update.message.reply_text(
        f"✅ Промокод {code} отключён."
    )


# =====================================================
# ВКЛ / ВЫКЛ ПОПОЛНЕНИЯ
# =====================================================

async def set_deposit_state(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    enabled: bool
):

    if not is_admin(update):
        await update.message.reply_text("❌ Нет доступа")
        return

    result = call_server(
        "admin_set_deposit_enabled",
        enabled=enabled,
    )

    if not result.get("ok"):
        await update.message.reply_text(
            "❌ " + result.get("error", "Ошибка")
        )
        return

    if enabled:
        await update.message.reply_text(
            "✅ Пополнение ВКЛЮЧЕНО.\n"
            "Игроки снова могут создавать заявки."
        )
    else:
        await update.message.reply_text(
            "⛔ Пополнение ОТКЛЮЧЕНО.\n"
            "Игроки увидят: «Пополнение временно недоступно»."
        )


async def deposit_minus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await set_deposit_state(update, context, False)


async def deposit_plus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await set_deposit_state(update, context, True)



# =====================================================
# ADMIN MENU + CHANNEL CONTROLS
# =====================================================

def admin_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("😈 MEM включён", callback_data="menu_mem"),
         InlineKeyboardButton("🍀 LUCK включён", callback_data="menu_luck")],
        [InlineKeyboardButton("📋 Все команды", callback_data="menu_commands")],
        [InlineKeyboardButton("⚙️ Статус пополнений", callback_data="menu_deposits")]
    ])

def commands_text():
    return (
        "📋 ВСЕ КОМАНДЫ\n\n"
        "/promo КОД АКТИВАЦИИ МОНЕТЫ — создать промо\n"
        "/promoff КОД — отключить промо\n"
        "/promoadd ID КОЛ-ВО — добавить право на создание промо\n"
        "/promotake ID КОЛ-ВО — убрать часть лимита\n"
        "/promoblock ID — забрать доступ\n"
        "/promoinfo ID — посмотреть остаток\n\n"
        "/- — отключить все пополнения\n"
        "/+ — включить все пополнения\n"
        "/g- — отключить только ГРН\n"
        "/g+ — включить только ГРН\n"
        "/b- — отключить только Brainrot\n"
        "/b+ — включить только Brainrot\n\n"
        "/mem+ TELEGRAM_ID — включить MEM\n"
        "/mem- TELEGRAM_ID — выключить MEM\n"
        "/luck+ TELEGRAM_ID — включить LUCK\n"
        "/luck- TELEGRAM_ID — выключить LUCK\n"
        "/menu — открыть это меню"
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    await update.message.reply_text(
        "🛠 ADMIN MENU\n\nВыбери раздел:",
        reply_markup=admin_menu_markup()
    )

async def set_channel(update, channel, enabled):
    if not is_admin(update):
        await update.message.reply_text("❌ Нет доступа")
        return
    result=call_server(
        "admin_set_deposit_channel_enabled",
        channel=channel,
        enabled=enabled
    )
    if not result.get("ok"):
        await update.message.reply_text("❌ "+result.get("error","Ошибка"))
        return
    name="ГРН" if channel=="uah" else "Brainrot + Герсы"
    await update.message.reply_text(
        ("✅ " if enabled else "⛔ ")+name+
        (" включено" if enabled else " отключено")
    )

async def g_minus_command(update, context): await set_channel(update,"uah",False)
async def g_plus_command(update, context): await set_channel(update,"uah",True)
async def b_minus_command(update, context): await set_channel(update,"brainrot",False)
async def b_plus_command(update, context): await set_channel(update,"brainrot",True)


# =====================================================
# КНОПКИ ЗАЯВОК
# =====================================================



# =====================================================
# TRADE BOT PICKER — dedicated callback handler
# Registered before the generic button handler so these
# buttons can never fall through to "Unknown button".
# =====================================================

TRADE_BOTS = [
    "brainroterXbot",
    "brainroterXbot1",
    "brainroterXbot2",
    "brainroterXbot3",
    "brainroterXbot4",
]

async def deposit_trade_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if query.from_user.id != ADMIN_TELEGRAM_ID:
        await query.answer("❌ Нет доступа", show_alert=True)
        return

    data = query.data or ""
    # Supported formats:
    # deposit_bot_<index>_<request_id>
    # deposit_trade_bot_<index>_<request_id>
    # trade_bot_<index>_<request_id>
    prefixes = ("deposit_bot_", "deposit_trade_bot_", "trade_bot_")
    prefix = next((p for p in prefixes if data.startswith(p)), None)
    if not prefix:
        await query.answer("❌ Неверная кнопка бота", show_alert=True)
        return

    tail = data[len(prefix):]
    parts = tail.split("_", 1)
    if len(parts) != 2:
        await query.answer("❌ Неверные данные кнопки", show_alert=True)
        return
    try:
        bot_index = int(parts[0])
        request_id = int(parts[1])
    except ValueError:
        await query.answer("❌ Неверные данные кнопки", show_alert=True)
        return

    if bot_index < 0 or bot_index >= len(TRADE_BOTS):
        await query.answer("❌ Неизвестный бот", show_alert=True)
        return

    bot_username = TRADE_BOTS[bot_index]
    result = call_server(
        "admin_assign_deposit_trade_bot",
        request_id=request_id,
        bot_username=bot_username,
    )
    if not result.get("ok"):
        await query.answer("❌ " + result.get("error", "Ошибка"), show_alert=True)
        return

    current_markup = query.message.reply_markup if query.message else None
    if current_markup:
        rows = []
        for row in current_markup.inline_keyboard:
            new_row = []
            for button in row:
                text = button.text.lstrip("✅ ")
                cb = button.callback_data
                if cb == data:
                    text = "✅ " + text
                kwargs = {"text": text}
                if cb is not None:
                    kwargs["callback_data"] = cb
                elif button.url is not None:
                    kwargs["url"] = button.url
                new_row.append(InlineKeyboardButton(**kwargs))
            rows.append(new_row)
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    await query.answer(f"✅ Выбран @{bot_username}")

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    if query.from_user.id != ADMIN_TELEGRAM_ID:

        await query.answer(
            "❌ Нет доступа",
            show_alert=True
        )

        return

    data = query.data or ""

    # Совместимость с разными версиями callback_data у кнопок вывода.
    # Нормализуем старые/альтернативные имена в текущие.
    callback_aliases = (
        ("withdraw_offline_", "withdraw_player_offline_"),
        ("withdraw_not_online_", "withdraw_player_offline_"),
        ("withdraw_player_not_online_", "withdraw_player_offline_"),
        ("withdraw_bad_username_", "withdraw_invalid_username_"),
        ("withdraw_wrong_username_", "withdraw_invalid_username_"),
        ("withdraw_invalid_nickname_", "withdraw_invalid_username_"),
        ("withdraw_wrong_nickname_", "withdraw_invalid_username_"),
    )
    for old_prefix, new_prefix in callback_aliases:
        if data.startswith(old_prefix):
            data = new_prefix + data[len(old_prefix):]
            break

    if data in ("menu_mem","menu_luck"):
        result=call_server("admin_get_mode_lists")
        if not result.get("ok"):
            await query.answer("❌ "+result.get("error","Ошибка"),show_alert=True)
            return
        key="mem_ids" if data=="menu_mem" else "luck_ids"
        title="😈 MEM ВКЛЮЧЁН" if data=="menu_mem" else "🍀 LUCK ВКЛЮЧЁН"
        ids=result.get(key,[])
        text=title+"\n\n"+("\n".join("• "+str(x) for x in ids) if ids else "Список пуст.")
        await query.answer()
        await query.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад",callback_data="menu_back")]]))
        return

    if data=="menu_commands":
        await query.answer()
        await query.edit_message_text(commands_text(),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад",callback_data="menu_back")]]))
        return

    if data=="menu_deposits":
        result=call_server("admin_get_deposit_channels")
        if not result.get("ok"):
            await query.answer("❌ "+result.get("error","Ошибка"),show_alert=True)
            return
        text=("⚙️ СТАТУС ПОПОЛНЕНИЙ\n\n"
              f"Общее: {'✅ ВКЛ' if result.get('deposit_enabled',True) else '⛔ ВЫКЛ'}\n"
              f"ГРН: {'✅ ВКЛ' if result.get('uah_enabled',True) else '⛔ ВЫКЛ'}\n"
              f"Brainrot + Герсы: {'✅ ВКЛ' if result.get('brainrot_enabled',True) else '⛔ ВЫКЛ'}")
        await query.answer()
        await query.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад",callback_data="menu_back")]]))
        return

    if data=="menu_back":
        await query.answer()
        await query.edit_message_text("🛠 ADMIN MENU\n\nВыбери раздел:",reply_markup=admin_menu_markup())
        return

    # Не вызываем query.answer() заранее:
    # при ошибке серверного запроса ниже будет показан alert,
    # а при успехе сообщение просто изменится.


    # =================================================
    # ГРН TEST — ПОДТВЕРДИТЬ
    # =================================================

    if data.startswith(
        "uah_approve_"
    ):

        request_id = data.replace(
            "uah_approve_",
            ""
        )

        try:
            request_id = int(
                request_id
            )
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_approve_uah_test_deposit",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer(
            "✅ Готово"
        )

        old_text = (
            query.message.text
            or ""
        )

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "✅ ГРН ЗАЯВКА ПОДТВЕРЖДЕНА"
            + "\n"
            + f"💰 Начислено: {result.get('added_coins', 0)} монет"
            + "\n"
            + f"🎯 Добавлен отыгрыш: {result.get('wager_added', 0)}"
        )

        return


    # =================================================
    # ГРН TEST — ОТКЛОНИТЬ
    # =================================================

    if data.startswith(
        "uah_reject_"
    ):

        request_id = data.replace(
            "uah_reject_",
            ""
        )

        try:
            request_id = int(
                request_id
            )
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_reject_uah_test_deposit",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer(
            "✅ Готово"
        )

        old_text = (
            query.message.text
            or ""
        )

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "❌ ГРН ЗАЯВКА ОТКЛОНЕНА"
        )

        return


    # =================================================
    # ГЕРСЫ — ПОДТВЕРДИТЬ
    # =================================================

    if data.startswith(
        "gear_approve_"
    ):

        request_id = data.replace(
            "gear_approve_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_approve_gear_deposit_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer(
            "✅ Готово"
        )

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "✅ ГЕРСЫ ПОДТВЕРЖДЕНЫ"
            + "\n"
            + f"💰 Начислено: {result.get('added_coins', 0)} монет"
            + "\n"
            + f"🎯 Добавлен отыгрыш: {result.get('wager_added', 0)}"
        )

        return


    # =================================================
    # ГЕРСЫ — ОТКЛОНИТЬ
    # =================================================

    if data.startswith(
        "gear_reject_"
    ):

        request_id = data.replace(
            "gear_reject_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_reject_gear_deposit_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer(
            "✅ Готово"
        )

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "❌ ГЕРСЫ ОТКЛОНЕНЫ"
        )

        return


    # =================================================
    # ПОПОЛНЕНИЕ — ВЫБРАТЬ БОТА ДЛЯ ТРЕЙДА
    # =================================================

    if data.startswith("deposit_bot_"):
        # Формат callback: deposit_bot_<index>_<request_id>
        parts = data.split("_", 3)
        if len(parts) != 4:
            await query.answer("❌ Неверная кнопка", show_alert=True)
            return

        try:
            bot_index = int(parts[2])
            request_id = int(parts[3])
        except ValueError:
            await query.answer("❌ Неверные данные", show_alert=True)
            return

        trade_bots = [
            "brainroterXbot",
            "brainroterXbot1",
            "brainroterXbot2",
            "brainroterXbot3",
            "brainroterXbot4",
        ]

        if bot_index < 0 or bot_index >= len(trade_bots):
            await query.answer("❌ Неизвестный бот", show_alert=True)
            return

        bot_username = trade_bots[bot_index]

        result = call_server(
            "admin_assign_deposit_trade_bot",
            request_id=request_id,
            bot_username=bot_username,
        )

        if not result.get("ok"):
            await query.answer(
                "❌ " + result.get("error", "Ошибка"),
                show_alert=True
            )
            return

        # Меняем только клавиатуру: заявка остаётся pending,
        # подтверждение и отмена остаются доступными.
        rows = []
        current_markup = query.message.reply_markup
        if current_markup:
            for row in current_markup.inline_keyboard:
                new_row = []
                for button in row:
                    button_text = button.text
                    callback_data = button.callback_data
                    if callback_data and callback_data.startswith("deposit_bot_"):
                        button_text = button_text.lstrip("✅ ")
                        if callback_data == data:
                            button_text = "✅ " + button_text
                    new_row.append(
                        InlineKeyboardButton(
                            button_text,
                            callback_data=callback_data,
                            url=button.url,
                        )
                    )
                rows.append(new_row)

        if rows:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(rows)
            )

        await query.answer(f"✅ Выбран @{bot_username}")
        return


    # =================================================
    # ПОПОЛНЕНИЕ — ПОДТВЕРДИТЬ
    # =================================================

    if data.startswith(
        "deposit_approve_"
    ):

        request_id = data.replace(
            "deposit_approve_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_approve_balance_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer("✅ Готово")

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "✅ ПОПОЛНЕНИЕ ПОДТВЕРЖДЕНО"
            + "\n"
            + f"💰 Начислено: {result.get('added_coins', 0)} монет"
            + "\n"
            + f"🎯 Добавлен отыгрыш: {result.get('wager_added', 0)}"
        )

        return


    # =================================================
    # ПОПОЛНЕНИЕ — ОТКЛОНИТЬ
    # =================================================

    if data.startswith(
        "deposit_reject_"
    ):

        request_id = data.replace(
            "deposit_reject_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_reject_balance_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer("✅ Готово")

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "❌ ПОПОЛНЕНИЕ ОТКЛОНЕНО"
        )

        return


    # =================================================
    # ВЫВОД — ПОДТВЕРДИТЬ
    # =================================================

    if data.startswith(
        "withdraw_approve_"
    ):

        request_id = data.replace(
            "withdraw_approve_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_approve_withdraw_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer("✅ Готово")

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "✅ ВЫВОД ПОДТВЕРЖДЁН"
            + "\n"
            + "Brainrot удалён из инвентаря."
        )

        return


    # =================================================
    # ВЫВОД — ОТКЛОНИТЬ
    # =================================================

    if data.startswith(
        "withdraw_reject_"
    ):

        request_id = data.replace(
            "withdraw_reject_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_reject_withdraw_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer("✅ Готово")

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "❌ ВЫВОД ОТКЛОНЁН"
            + "\n"
            + "Brainrot снова доступен игроку."
        )

        return


    # =================================================
    # ВЫВОД — НЕТ В НАЛИЧИИ
    # =================================================

    if data.startswith(
        "withdraw_out_of_stock_"
    ):

        request_id = data.replace(
            "withdraw_out_of_stock_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_out_of_stock_withdraw_request",
            request_id=request_id,
        )

        if not result.get("ok"):

            await query.answer(
                "❌ "
                + result.get(
                    "error",
                    "Ошибка"
                ),
                show_alert=True
            )

            return

        await query.answer("✅ Готово")

        old_text = query.message.text or ""

        await query.edit_message_text(
            old_text
            + "\n\n"
            + "📦 НЕТ В НАЛИЧИИ"
            + "\n"
            + "Brainrot разблокирован."
            + "\n"
            + "Игроку отправлено уведомление."
        )

        return


    # =================================================
    # ВЫВОД — ИГРОК НЕ В СЕТИ
    # =================================================

    if data.startswith(
        "withdraw_player_offline_"
    ):

        request_id = data.replace(
            "withdraw_player_offline_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_cancel_withdraw_request",
            request_id=request_id,
            cancel_reason="player_offline",
        )

        if not result.get("ok"):
            await query.answer(
                "❌ " + result.get("error", "Ошибка"),
                show_alert=True
            )
            return

        await query.answer("✅ Вывод отменён")
        old_text = query.message.text or ""
        await query.edit_message_text(
            old_text
            + "\n\n"
            + "📴 ВЫВОД ОТМЕНЁН — ИГРОК НЕ В СЕТИ"
            + "\nBrainrot снова доступны игроку."
            + "\nИгроку отправлено уведомление."
        )
        return


    # =================================================
    # ВЫВОД — НЕВЕРНЫЙ НИКНЕЙМ
    # =================================================

    if data.startswith(
        "withdraw_invalid_username_"
    ):

        request_id = data.replace(
            "withdraw_invalid_username_",
            ""
        )

        try:
            request_id = int(request_id)
        except ValueError:
            await query.answer(
                "❌ Неверный ID заявки",
                show_alert=True
            )
            return

        result = call_server(
            "admin_cancel_withdraw_request",
            request_id=request_id,
            cancel_reason="invalid_username",
        )

        if not result.get("ok"):
            await query.answer(
                "❌ " + result.get("error", "Ошибка"),
                show_alert=True
            )
            return

        await query.answer("✅ Вывод отменён")
        old_text = query.message.text or ""
        await query.edit_message_text(
            old_text
            + "\n\n"
            + "✏️ ВЫВОД ОТМЕНЁН — НЕВЕРНЫЙ НИКНЕЙМ"
            + "\nBrainrot снова доступны игроку."
            + "\nИгроку отправлено уведомление."
        )
        return


    await query.answer(
        "❌ Неизвестная кнопка",
        show_alert=True
    )



# =====================================================
# MEM VISUAL PRANK
# =====================================================

async def mem_plus_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):

        await update.message.reply_text(
            "❌ Нет доступа"
        )

        return

    parts = (
        update.message.text
        or ""
    ).strip().split()

    if len(parts) != 2:

        await update.message.reply_text(
            "Использование:\n"
            "/mem+ TELEGRAM_ID"
        )

        return

    try:

        target_telegram_id = int(
            parts[1]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Telegram ID должен быть числом"
        )

        return

    result = call_server(
        "admin_set_visual_prank",
        target_telegram_id=target_telegram_id,
        enabled=True,
    )

    if not result.get("ok"):

        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )

        return

    await update.message.reply_text(
        "😈 MEM включён\n"
        f"Telegram ID: {target_telegram_id}\n"
        "Шансы и награды не меняются.\n"
        "Проигрыши визуально чаще останавливаются рядом с зоной."
    )


async def mem_minus_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):

        await update.message.reply_text(
            "❌ Нет доступа"
        )

        return

    parts = (
        update.message.text
        or ""
    ).strip().split()

    if len(parts) != 2:

        await update.message.reply_text(
            "Использование:\n"
            "/mem- TELEGRAM_ID"
        )

        return

    try:

        target_telegram_id = int(
            parts[1]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Telegram ID должен быть числом"
        )

        return

    result = call_server(
        "admin_set_visual_prank",
        target_telegram_id=target_telegram_id,
        enabled=False,
    )

    if not result.get("ok"):

        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )

        return

    await update.message.reply_text(
        "🙂 MEM выключен\n"
        f"Telegram ID: {target_telegram_id}"
    )




# =====================================================
# LUCK MODE
# =====================================================

async def luck_plus_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await update.message.reply_text(
            "❌ Нет доступа"
        )
        return

    parts = (
        update.message.text
        or ""
    ).strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Использование:\n"
            "/luck+ TELEGRAM_ID"
        )
        return

    try:
        target_telegram_id = int(
            parts[1]
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Telegram ID должен быть числом"
        )
        return

    result = call_server(
        "admin_set_luck_mode",
        target_telegram_id=target_telegram_id,
        enabled=True,
    )

    if not result.get("ok"):
        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )
        return

    await update.message.reply_text(
        "🍀 LUCK включён\n"
        f"Telegram ID: {target_telegram_id}\n"
        "Серверный шанс апгрейда минимум 70%."
    )


async def luck_minus_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await update.message.reply_text(
            "❌ Нет доступа"
        )
        return

    parts = (
        update.message.text
        or ""
    ).strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Использование:\n"
            "/luck- TELEGRAM_ID"
        )
        return

    try:
        target_telegram_id = int(
            parts[1]
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Telegram ID должен быть числом"
        )
        return

    result = call_server(
        "admin_set_luck_mode",
        target_telegram_id=target_telegram_id,
        enabled=False,
    )

    if not result.get("ok"):
        await update.message.reply_text(
            "❌ "
            + result.get(
                "error",
                "Ошибка"
            )
        )
        return

    await update.message.reply_text(
        "🍀 LUCK выключен\n"
        f"Telegram ID: {target_telegram_id}"
    )


# =====================================================
# MEM TEXT ROUTER
# Telegram command entities do not reliably support +/-
# so /mem+ and /mem- are parsed as plain text here.
# =====================================================

async def mem_text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    text = (
        message.text
        or ""
    ).strip()

    lower = text.lower()

    if lower.startswith("/mem+"):

        await mem_plus_command(
            update,
            context
        )

        return

    if lower.startswith("/mem-"):

        await mem_minus_command(
            update,
            context
        )

        return

    if lower.startswith("/luck+"):

        await luck_plus_command(
            update,
            context
        )

        return

    if lower.startswith("/luck-"):

        await luck_minus_command(
            update,
            context
        )

        return


# =====================================================
# ЗАПУСК
# =====================================================

def main():

    print(
        "ADMIN BOT ЗАПУЩЕН"
    )

    app = (
        ApplicationBuilder()
        .token(ADMIN_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    app.add_handler(
        CommandHandler(
            "menu",
            menu_command
        )
    )

    app.add_handler(
        CommandHandler(
            "promo",
            promo_command
        )
    )

    app.add_handler(
        CommandHandler(
            "promoff",
            promoff_command
        )
    )

    app.add_handler(CommandHandler("promoadd", promoadd_command))
    app.add_handler(CommandHandler("promotake", promotake_command))
    app.add_handler(CommandHandler("promoblock", promoblock_command))
    app.add_handler(CommandHandler("promoinfo", promoinfo_command))

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/-$"),
            deposit_minus
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/\+$"),
            deposit_plus
        )
    )

    app.add_handler(MessageHandler(filters.Regex(r"^/g-$"), g_minus_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/g\+$"), g_plus_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/b-$"), b_minus_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/b\+$"), b_plus_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT,
            mem_text_router
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deposit_trade_bot_handler,
            pattern=r"^(deposit_bot_|deposit_trade_bot_|trade_bot_)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()