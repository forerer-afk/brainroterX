import os
import requests
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonWebApp,
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
)


# =========================================================
# BRAINROTER X
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()


# =========================================================
# MINI APP URL
#
# После обновления index.html меняй цифру после ?v=
# =========================================================

MINI_APP_URL = "https://forerer-afk.github.io/brainroterX/?v=500"


if not TOKEN:
    raise RuntimeError(
        "В .env не найден BOT_TOKEN"
    )

if not SUPABASE_URL:
    raise RuntimeError(
        "В .env не найден SUPABASE_URL"
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "В .env не найден SUPABASE_KEY"
    )


# =========================================================
# SUPABASE HEADERS
# =========================================================

def supabase_headers():

    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def service_headers():

    key = SUPABASE_SERVICE_ROLE_KEY

    if not key:
        raise RuntimeError(
            "Для Stars добавь SUPABASE_SERVICE_ROLE_KEY в Railway Variables"
        )

    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_star_request(request_id):

    url = (
        f"{SUPABASE_URL}/rest/v1/star_deposit_requests"
        f"?id=eq.{request_id}"
        f"&select=*"
        f"&limit=1"
    )

    response = requests.get(
        url,
        headers=service_headers(),
        timeout=15
    )

    if not response.ok:
        print("Stars request read error:", response.status_code, response.text)
        return None

    rows = response.json()
    return rows[0] if rows else None


def complete_star_request(request_id, telegram_id, payment):

    url = f"{SUPABASE_URL}/rest/v1/rpc/complete_star_deposit"

    payload = {
        "p_request_id": request_id,
        "p_telegram_id": telegram_id,
        "p_currency": payment.currency,
        "p_total_amount": payment.total_amount,
        "p_telegram_payment_charge_id": payment.telegram_payment_charge_id,
        "p_provider_payment_charge_id": payment.provider_payment_charge_id or "",
    }

    response = requests.post(
        url,
        headers=service_headers(),
        json=payload,
        timeout=20
    )

    if not response.ok:
        raise RuntimeError(
            f"Supabase Stars RPC: {response.status_code} {response.text}"
        )

    return response.json()


def send_admin_star_notice(text):

    if not ADMIN_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("ADMIN_BOT_TOKEN / ADMIN_CHAT_ID не настроены — уведомление Stars пропущено")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text,
            },
            timeout=15
        )
    except Exception as error:
        print("Ошибка уведомления админа Stars:", error)


# =========================================================
# ПРОВЕРКА ИГРОКА
# =========================================================

def get_player(telegram_id):

    url = (
        f"{SUPABASE_URL}/rest/v1/players"
        f"?telegram_id=eq.{telegram_id}"
        f"&select=*"
        f"&limit=1"
    )

    response = requests.get(
        url,
        headers=supabase_headers(),
        timeout=15
    )

    if not response.ok:
        print(
            "Ошибка проверки игрока:",
            response.status_code,
            response.text
        )

        return None


    data = response.json()

    if not data:
        return None

    return data[0]


# =========================================================
# СОЗДАНИЕ НОВОГО ИГРОКА
# =========================================================

def create_player(telegram_id):

    url = (
        f"{SUPABASE_URL}/rest/v1/players"
    )

    data = {
        "telegram_id": telegram_id,
        "coins": 0,
        "cases_opened": 0,
        "upgrades_done": 0,
        "has_deposited": False,
        "wager_required": 0,
        "wager_progress": 0,
    }

    headers = supabase_headers()

    headers["Prefer"] = (
        "return=representation"
    )

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=15
    )

    if not response.ok:

        print(
            "Ошибка создания игрока:",
            response.status_code,
            response.text
        )

        return None


    result = response.json()

    if result:
        return result[0]

    return None


# =========================================================
# СОЗДАТЬ ИГРОКА, ЕСЛИ ЕГО НЕТ
# =========================================================

def ensure_player(telegram_id):

    player = get_player(
        telegram_id
    )

    if player:
        return player


    print(
        "Новый игрок:",
        telegram_id
    )


    player = create_player(
        telegram_id
    )

    if player:

        print(
            "Игрок создан:",
            telegram_id
        )


    return player


# =========================================================
# КНОПКА ИГРАТЬ
# =========================================================

def game_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(

                    text="🎮 ИГРАТЬ",

                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    )

                )
            ]
        ]
    )


# =========================================================
# MINI APP MENU ДЛЯ ИГРОКА
# =========================================================

async def set_player_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat

    if not chat:
        return


    try:

        await context.bot.set_chat_menu_button(

            chat_id=chat.id,

            menu_button=MenuButtonWebApp(

                text="🎮 Играть",

                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )

            )

        )

    except Exception as error:

        print(
            "Ошибка Mini App меню:",
            error
        )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return


    telegram_id = user.id


    # =====================================================
    # ВАЖНО:
    # Создаём игрока в Supabase
    # ДО того, как даём открыть Mini App
    # =====================================================

    player = ensure_player(
        telegram_id
    )


    if not player:

        await update.message.reply_text(

            "❌ Не удалось создать игровой аккаунт.\n"
            "Попробуй ещё раз через несколько секунд."

        )

        return


    await set_player_menu(
        update,
        context
    )


    name = (
        user.first_name
        or
        "Игрок"
    )


    await update.message.reply_text(

        f"👋 Привет, {name}!\n\n"

        "Добро пожаловать в "
        "Brainroter X 🧠🔥\n\n"

        "Открывай кейсы, "
        "используй апгрейдер "
        "и собирай Brainrot.\n\n"

        "Готов начать игру?",

        reply_markup=game_keyboard()

    )


# =========================================================
# /PLAY
# =========================================================

async def play(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return


    player = ensure_player(
        user.id
    )


    if not player:

        await update.message.reply_text(
            "❌ Не удалось загрузить игровой аккаунт."
        )

        return


    await set_player_menu(
        update,
        context
    )


    await update.message.reply_text(

        "🎮 Нажми кнопку ниже, "
        "чтобы открыть Brainroter X:",

        reply_markup=game_keyboard()

    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🎮 Brainroter X\n\n"

        "/start — создать аккаунт / открыть игру\n"

        "/play — открыть игру\n"

        "/help — помощь"

    )


# =========================================================
# ГЛОБАЛЬНАЯ КНОПКА
# =========================================================

async def post_init(
    application: Application
):

    try:

        await application.bot.set_chat_menu_button(

            menu_button=MenuButtonWebApp(

                text="🎮 Играть",

                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )

            )

        )


        print(
            "Глобальная Mini App кнопка установлена"
        )


    except Exception as error:

        print(
            "Ошибка глобальной кнопки:",
            error
        )


# =========================================================
# TELEGRAM STARS
# =========================================================

def parse_star_payload(payload):

    try:
        prefix, request_id, telegram_id = str(payload).split(":", 2)
        if prefix != "brainroterx_stars":
            return None
        return int(request_id), int(telegram_id)
    except Exception:
        return None


async def stars_precheckout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.pre_checkout_query

    if not query:
        return

    parsed = parse_star_payload(query.invoice_payload)

    if not parsed:
        await query.answer(
            ok=False,
            error_message="Неверный счёт BrainroterX."
        )
        return

    request_id, payload_telegram_id = parsed

    try:
        request = get_star_request(request_id)

        valid = (
            request
            and request.get("status") == "pending"
            and int(request.get("telegram_id", 0)) == query.from_user.id
            and payload_telegram_id == query.from_user.id
            and query.currency == "XTR"
            and int(request.get("stars", 0)) == query.total_amount
        )

        if not valid:
            await query.answer(
                ok=False,
                error_message="Счёт устарел или сумма не совпадает. Создай новый счёт в игре."
            )
            return

        await query.answer(ok=True)

    except Exception as error:
        print("Stars precheckout error:", error)
        await query.answer(
            ok=False,
            error_message="Не удалось проверить платёж. Попробуй ещё раз."
        )


async def stars_successful_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.successful_payment:
        return

    payment = message.successful_payment
    parsed = parse_star_payload(payment.invoice_payload)

    if not parsed:
        return

    request_id, payload_telegram_id = parsed

    if payload_telegram_id != user.id:
        print("Stars payment payload user mismatch")
        return

    try:
        result = complete_star_request(
            request_id,
            user.id,
            payment
        )

        added_coins = int(result.get("added_coins", 0))
        already = bool(result.get("already_processed"))

        if not already:
            await message.reply_text(
                f"✅ Оплата Stars прошла!\n\n"
                f"⭐ Оплачено: {payment.total_amount}\n"
                f"💰 Начислено: {added_coins} ⓧ\n"
                f"🧾 Заявка: #{request_id}"
            )

            username = f"@{user.username}" if user.username else "без username"
            send_admin_star_notice(
                f"⭐ ПОПОЛНЕНИЕ STARS #{request_id}\n\n"
                f"👤 {user.first_name or 'Игрок'} ({username})\n"
                f"🆔 {user.id}\n"
                f"⭐ Оплачено: {payment.total_amount}\n"
                f"ⓧ Начислено: {added_coins}\n"
                f"✅ Подтверждено автоматически"
            )

    except Exception as error:
        print("Stars successful payment error:", error)
        # Payment уже состоялся. Не выдаём повторно и не подтверждаем вручную.
        # Ошибка остаётся в логах, чтобы её можно было безопасно разобрать по charge_id.
        await message.reply_text(
            "⚠️ Платёж Telegram получен, но возникла ошибка начисления. "
            "Не оплачивай повторно — администратор сможет проверить платёж по операции."
        )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "Ошибка:",
        context.error
    )


# =========================================================
# START BOT
# =========================================================

def main():

    app = (

        Application
        .builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()

    )


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "play",
            play
        )
    )


    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )


    app.add_handler(
        PreCheckoutQueryHandler(
            stars_precheckout
        )
    )

    app.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            stars_successful_payment
        )
    )


    app.add_error_handler(
        error_handler
    )


    print(
        "brainroterX запущен!"
    )

    print(
        "Mini App URL:",
        MINI_APP_URL
    )


    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()