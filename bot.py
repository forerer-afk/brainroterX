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
)


# =========================================================
# BRAINROTER X
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


# =========================================================
# MINI APP URL
#
# После обновления index.html меняй цифру после ?v=
# =========================================================

MINI_APP_URL = "https://forerer-afk.github.io/brainroterX/?v=501"


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
