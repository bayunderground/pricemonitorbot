import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from pricemonitorbot.db.models import User
from pricemonitorbot.db.repositories.products import get_user_products, remove_product
from pricemonitorbot.db.session import get_session

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("list"))
async def cmd_list(message: Message, db_user: User) -> None:
    async with get_session() as session:
        products = await get_user_products(session, db_user.id)

    if not products:
        await message.answer("У вас нет отслеживаемых товаров.\nДобавьте первый товар командой /add")
        return

    lines = []
    for i, p in enumerate(products, 1):
        price_str = f"{p.last_price:.2f} ₽" if p.last_price else "—"
        stock_str = "✅" if p.last_in_stock else "❌"
        title = p.title or p.external_id
        lines.append(f"{i}. {title}\n   💰 {price_str} | {stock_str}")

    await message.answer("Ваши товары:\n\n" + "\n".join(lines))


@router.message(Command("remove"))
async def cmd_remove(message: Message, db_user: User) -> None:
    async with get_session() as session:
        products = await get_user_products(session, db_user.id)

    if not products:
        await message.answer("Нечего удалять — список товаров пуст.")
        return

    buttons = []
    for p in products:
        title = p.title or p.external_id
        if len(title) > 30:
            title = title[:27] + "..."
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"remove:{p.id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите товар для удаления:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("remove:"))
async def callback_remove(callback: CallbackQuery, db_user: User) -> None:
    product_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        removed = await remove_product(session, product_id, db_user.id)

    if removed:
        await callback.message.edit_text("Товар удалён из отслеживания.")
    else:
        await callback.answer("Товар не найден или уже удалён.", show_alert=True)
