import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message

from pricemonitorbot.db.models import User
from pricemonitorbot.db.repositories.subscriptions import get_active_subscription
from pricemonitorbot.db.session import get_session

logger = logging.getLogger(__name__)
router = Router()

TARIFFS = {
    "start": {"title": "Start", "max_products": 5, "price": 149},
    "business": {"title": "Business", "max_products": 25, "price": 399},
    "pro": {"title": "Pro", "max_products": 100, "price": 899},
}


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, db_user: User) -> None:
    async with get_session() as session:
        sub = await get_active_subscription(session, db_user.id)
        if sub:
            await message.answer("У вас уже есть активная подписка. Проверьте /status")
            return

    buttons = [
        [
            InlineKeyboardButton(
                text="Start — до 5 товаров — 149 ⭐/мес",
                callback_data="sub:start",
            )
        ],
        [
            InlineKeyboardButton(
                text="Business — до 25 товаров — 399 ⭐/мес",
                callback_data="sub:business",
            )
        ],
        [
            InlineKeyboardButton(
                text="Pro — до 100 товаров — 899 ⭐/мес",
                callback_data="sub:pro",
            )
        ],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "Выберите тариф для подписки:\n\n"
        "Start — до 5 товаров — 149 ⭐/мес\n"
        "Business — до 25 товаров — 399 ⭐/мес\n"
        "Pro — до 100 товаров — 899 ⭐/мес",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("sub:"))
async def callback_subscribe(callback: CallbackQuery, db_user: User) -> None:
    tariff_code = callback.data.split(":")[1]
    tariff = TARIFFS.get(tariff_code)
    if not tariff:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    bot = callback.bot

    payload = f"sub:{tariff_code}:{db_user.id}"

    try:
        invoice_link = await bot.create_invoice_link(
            title=f"Подписка {tariff['title']}",
            description=f"Отслеживание до {tariff['max_products']} товаров на Wildberries",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=f"Подписка {tariff['title']}", amount=tariff["price"])],
            subscription_period=2592000,
            provider_token="",
        )

        await callback.message.answer(
            f"Оформление подписки {tariff['title']}:\n"
            f"- До {tariff['max_products']} товаров\n"
            f"- {tariff['price']} ⭐/мес\n\n"
            f"Нажмите кнопку ниже для оплаты:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"Оплатить {tariff['price']} ⭐", url=invoice_link)]
                ]
            ),
        )
    except Exception:
        logger.exception("Failed to create invoice link for tariff %s", tariff_code)
        await callback.message.answer("Ошибка при создании счёта. Попробуйте позже.")

    await callback.answer()
