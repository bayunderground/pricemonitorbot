import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from pricemonitorbot.db.models import User
from pricemonitorbot.db.repositories.products import count_user_products
from pricemonitorbot.db.repositories.subscriptions import get_active_subscription
from pricemonitorbot.db.session import get_session

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("status"))
async def cmd_status(message: Message, db_user: User) -> None:
    async with get_session() as session:
        sub = await get_active_subscription(session, db_user.id)
        product_count = await count_user_products(session, db_user.id)

    if sub is None:
        limit = 5
        await message.answer(
            f"Статус: бесплатный тариф\n\n"
            f"📦 Товаров: {product_count} из {limit}\n"
            f"💡 Оформите подписку для увеличения лимита\n\n"
            f"/subscribe — выбрать тариф",
        )
        return

    await sub.awaitable_attrs.plan
    plan = sub.plan

    limit = plan.max_products if plan else 5
    period_end = sub.current_period_end.strftime("%d.%m.%Y") if sub.current_period_end else "—"

    await message.answer(
        f"Статус подписки: {plan.title if plan else '—'}\n\n"
        f"📦 Товаров: {product_count} из {limit}\n"
        f"📅 Следующее списание: {period_end}\n\n"
        f"/subscribe — сменить тариф",
    )
