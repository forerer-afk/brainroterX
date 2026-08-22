import os
from telegram import Update
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


# =====================================================
# /START
# =====================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):

        await update.message.reply_text(
            "❌ Нет доступа"
        )

        return

    await update.message.reply_text(
        "🛠 ADMIN BOT\n\n"
        "Создать промокод:\n"
        "/promo КОД АКТИВАЦИИ МОНЕТЫ\n\n"
        "Пример:\n"
        "/promo lavaka676 5 5\n\n"
        "Отключить промокод:\n"
        "/promoff lavaka676\n\n"
        "⛔ Отключить пополнение: /-\n"
        "✅ Включить пополнение: /+"
    )


# =====================================================
# СОЗДАНИЕ ПРОМОКОДА
# =====================================================

async def promo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):

        await update.message.reply_text(
            "❌ Нет доступа"
        )

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
# КНОПКИ ЗАЯВОК
# =====================================================

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

    # Не вызываем query.answer() заранее:
    # при ошибке серверного запроса ниже будет показан alert,
    # а при успехе сообщение просто изменится.

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


    await query.answer(
        "❌ Неизвестная кнопка",
        show_alert=True
    )


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

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
