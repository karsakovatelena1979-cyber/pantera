import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, FSInputFile
)
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID, VIDEO_ARCHIVE_PATH, STARS_PRICE
from database import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()


# ─────────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────────

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Получить за 25 ⭐", callback_data="buy_stars")],
        [InlineKeyboardButton(text="🆓 Получить бесплатно", callback_data="free")],
    ])


def admin_keyboard(user_id: int, request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{user_id}_{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}_{request_id}"),
        ]
    ])


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Заявки на рассмотрении", callback_data="admin_pending")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    ])


# ─────────────────────────────────────────────
#  START
# ─────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await db.add_user(message.from_user.id, message.from_user.username or "")
    await message.answer(
        "👋 Привет!\n\n"
        "Если хочешь посмотреть видео с Казани, нажимай сюда 👇",
        reply_markup=main_keyboard()
    )


# ─────────────────────────────────────────────
#  ПЛАТНАЯ ПОКУПКА (Telegram Stars)
# ─────────────────────────────────────────────

@dp.callback_query(F.data == "buy_stars")
async def buy_stars(call: CallbackQuery):
    await call.answer()
    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="📁 Папка с видео из Казани — Пантера",
        description="После оплаты папка с видео придёт моментально! 🎬",
        payload="pantera_video",
        currency="XTR",
        prices=[LabeledPrice(label="Папка с видео", amount=STARS_PRICE)],
    )


@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    await db.add_paid_user(user_id)
    await message.answer("✅ Оплата прошла! Отправляю папку с видео прямо сейчас...")
    await send_video_archive(message.chat.id)
    # Уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>Новая покупка!</b>\n\n"
        f"👤 Пользователь: @{message.from_user.username or 'без ника'}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"⭐ Оплачено: {STARS_PRICE} Stars",
        parse_mode="HTML"
    )


# ─────────────────────────────────────────────
#  БЕСПЛАТНЫЙ СПОСОБ
# ─────────────────────────────────────────────

FREE_TASK_TEXT = (
    "Чтобы получить папку с видео из Казани, выполни это:\n\n"
    "<code>кому видео из Казани? (@ka3an_v1de0)</code>\n\n"
    "<b>Отправь этот текст в комментарии под 10 видео с пантерой в TikTok.</b>\n"
    "<b>После этого отправь ВСЕ 10 скриншотов одним сообщением сюда в бота — "
    "администратор рассмотрит заявку, и после принятия папка придёт моментально! 🚀</b>"
)


@dp.callback_query(F.data == "free")
async def free_option(call: CallbackQuery):
    await call.answer()
    await call.message.answer(FREE_TASK_TEXT, parse_mode="HTML")
    await db.set_user_state(call.from_user.id, "waiting_screenshots")


# ─────────────────────────────────────────────
#  ПРИЁМ СКРИНШОТОВ
# ─────────────────────────────────────────────

@dp.message(F.media_group_id | F.photo)
async def receive_screenshots(message: Message):
    user_id = message.from_user.id
    state = await db.get_user_state(user_id)

    if state != "waiting_screenshots":
        return

    # Проверяем, не отправил ли уже заявку
    if await db.has_pending_request(user_id):
        await message.answer(
            "⏳ Твоя заявка уже на рассмотрении. Подожди ответа администратора!"
        )
        return

    request_id = await db.create_request(user_id, message.message_id)
    await db.set_user_state(user_id, "request_sent")

    await message.answer(
        "📨 Скриншоты получены! После написания ожидай ответа от администратора ⏳"
    )

    # Пересылаем фото(ы) в чат админа
    username = message.from_user.username or "без ника"
    full_name = message.from_user.full_name

    await bot.send_message(
        ADMIN_ID,
        f"📸 <b>Новая заявка на бесплатное получение!</b>\n\n"
        f"👤 Имя: {full_name}\n"
        f"🔗 Username: @{username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📋 Заявка #{request_id}\n\n"
        f"Проверь скриншоты ниже 👇",
        parse_mode="HTML",
        reply_markup=admin_keyboard(user_id, request_id)
    )
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)


# ─────────────────────────────────────────────
#  ДЕЙСТВИЯ АДМИНА
# ─────────────────────────────────────────────

@dp.callback_query(F.data.startswith("approve_"))
async def approve_request(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ У тебя нет прав!", show_alert=True)
        return

    _, user_id, request_id = call.data.split("_")
    user_id, request_id = int(user_id), int(request_id)

    await db.update_request_status(request_id, "approved")
    await db.set_user_state(user_id, "received")

    await bot.send_message(
        user_id,
        "🎉 <b>Твоя заявка одобрена!</b>\n\nОтправляю папку с видео прямо сейчас... 🚀",
        parse_mode="HTML"
    )
    await send_video_archive(user_id)

    await call.message.edit_text(
        call.message.text + f"\n\n✅ <b>Заявка #{request_id} одобрена!</b>",
        parse_mode="HTML"
    )
    await call.answer("✅ Заявка одобрена, видео отправлено!")


@dp.callback_query(F.data.startswith("reject_"))
async def reject_request(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ У тебя нет прав!", show_alert=True)
        return

    _, user_id, request_id = call.data.split("_")
    user_id, request_id = int(user_id), int(request_id)

    await db.update_request_status(request_id, "rejected")
    await db.set_user_state(user_id, "waiting_screenshots")

    await bot.send_message(
        user_id,
        "❌ <b>Ваша заявка отклонена.</b>\n\n"
        "Если ты выполнил задание — попробуй снова, убедившись, что все 10 скриншотов отправлены одним сообщением.",
        parse_mode="HTML"
    )

    await call.message.edit_text(
        call.message.text + f"\n\n❌ <b>Заявка #{request_id} отклонена.</b>",
        parse_mode="HTML"
    )
    await call.answer("❌ Заявка отклонена!")


# ─────────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────────

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "🛠 <b>Панель администратора</b>\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    stats = await db.get_stats()
    await call.message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"💰 Купивших за Stars: <b>{stats['paid_users']}</b>\n"
        f"📋 Заявок всего: <b>{stats['total_requests']}</b>\n"
        f"⏳ Ожидают решения: <b>{stats['pending_requests']}</b>\n"
        f"✅ Одобрено: <b>{stats['approved_requests']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected_requests']}</b>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.callback_query(F.data == "admin_pending")
async def admin_pending(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    requests = await db.get_pending_requests()
    if not requests:
        await call.message.answer("✅ Нет заявок на рассмотрении!")
        await call.answer()
        return

    text = "📋 <b>Заявки на рассмотрении:</b>\n\n"
    for r in requests:
        text += f"🆔 ID: <code>{r['user_id']}</code> | @{r['username']} | Заявка #{r['id']}\n"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    await call.message.answer(
        "📢 Отправь текст для рассылки командой:\n\n"
        "<code>/broadcast Текст рассылки</code>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("❗ Укажи текст: /broadcast Текст")
        return

    users = await db.get_all_users()
    sent, failed = 0, 0

    await message.answer(f"📢 Начинаю рассылку для {len(users)} пользователей...")

    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"💰 Купили за Stars: <b>{stats['paid_users']}</b>\n"
        f"📋 Заявок: {stats['total_requests']} (⏳{stats['pending_requests']} / ✅{stats['approved_requests']} / ❌{stats['rejected_requests']})",
        parse_mode="HTML"
    )


@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = await db.get_all_users_info()
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    text = "👥 <b>Список пользователей:</b>\n\n"
    for u in users[:50]:
        text += f"• <code>{u['user_id']}</code> @{u['username'] or '—'}\n"
    if len(users) > 50:
        text += f"\n... и ещё {len(users) - 50}"
    await message.answer(text, parse_mode="HTML")


# ─────────────────────────────────────────────
#  ОТПРАВКА АРХИВА
# ─────────────────────────────────────────────

async def send_video_archive(chat_id: int):
    try:
        archive = FSInputFile(VIDEO_ARCHIVE_PATH, filename="пантера.zip")
        await bot.send_document(
            chat_id,
            archive,
            caption=(
                "📁 <b>Папка с видео из Казани — Пантера</b>\n\n"
                "Наслаждайся! 🎬🔥"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки архива для {chat_id}: {e}")
        await bot.send_message(
            chat_id,
            "⚠️ Произошла ошибка при отправке файла. Напиши администратору."
        )
        await bot.send_message(
            ADMIN_ID,
            f"⚠️ Ошибка отправки архива пользователю {chat_id}: {e}"
        )


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

async def main():
    await db.init()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
