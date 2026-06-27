import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from pricemonitorbot.db.models import MarketplaceType, User
from pricemonitorbot.db.repositories.products import (
    add_product,
    count_user_products,
    get_product_by_external_id,
)
from pricemonitorbot.db.repositories.subscriptions import get_user_product_limit
from pricemonitorbot.db.session import get_session
from pricemonitorbot.parsers import WildberriesParser
from pricemonitorbot.parsers.wildberries import normalize_wb_input

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("add"))
async def cmd_add(message: Message, db_user: User) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /add <ссылка или артикул>\n\nПримеры:\n/add 123456789\n/add https://www.wildberries.ru/catalog/123456789/detail.aspx")
        return

    raw_input = args[1].strip()
    sku = normalize_wb_input(raw_input)
    if not sku:
        await message.answer("Не удалось распознать артикул. Отправьте ссылку на товар или числовой артикул.")
        return

    async with get_session() as session:
        existing = await get_product_by_external_id(session, db_user.id, sku)
        if existing:
            await message.answer(f"Товар {sku} уже отслеживается.")
            return

        product_count = await count_user_products(session, db_user.id)
        limit = await get_user_product_limit(session, db_user.id)
        if product_count >= limit:
            await message.answer(
                f"Достигнут лимит в {limit} товаров.\n"
                "Оформите подписку командой /subscribe для увеличения лимита."
            )
            return

    status_msg = await message.answer("Получаю информацию о товаре...")

    parser = WildberriesParser()
    result = await parser.fetch(raw_input)

    if result.error:
        await status_msg.edit_text(f"Ошибка: {result.error}")
        return

    async with get_session() as session:
        await add_product(
            session=session,
            user_id=db_user.id,
            marketplace=MarketplaceType.wildberries,
            external_id=sku,
            url=raw_input if raw_input.startswith("http") else f"https://www.wildberries.ru/catalog/{sku}/detail.aspx",
            title=result.title,
            price=result.price,
            in_stock=result.in_stock,
        )

    price_str = f"{result.price:.2f} ₽" if result.price else "неизвестна"
    stock_str = "в наличии" if result.in_stock else "нет в наличии"
    title_str = result.title or sku

    await status_msg.edit_text(
        f"Товар добавлен!\n\n"
        f"📦 {title_str}\n"
        f"💰 Цена: {price_str}\n"
        f"📊 Наличие: {stock_str}"
    )
