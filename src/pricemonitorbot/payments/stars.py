import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiogram import Router
from aiogram.types import Message

from pricemonitorbot.db.models import User
from pricemonitorbot.db.repositories.payments import payment_exists, record_payment
from pricemonitorbot.db.repositories.subscriptions import create_subscription, get_active_subscription, renew_subscription
from pricemonitorbot.db.session import get_session
from pricemonitorbot.db.models import SubscriptionPlan

logger = logging.getLogger(__name__)
router = Router()


@router.message(lambda m: m.successful_payment is not None)
async def handle_successful_payment(message: Message, db_user: User) -> None:
    payment = message.successful_payment
    if payment is None:
        return

    charge_id = payment.telegram_payment_charge_id
    if not charge_id:
        logger.error("Successful payment without charge_id from user %s", db_user.id)
        return

    async with get_session() as session:
        if await payment_exists(session, charge_id):
            logger.info("Duplicate payment %s, ignoring", charge_id)
            await message.answer("Платёж уже обработан.")
            return

        payload = payment.invoice_payload or ""
        parts = payload.split(":")
        tariff_code = parts[1] if len(parts) >= 2 else "start"

        from sqlalchemy import select

        result = await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.code == tariff_code)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            result = await session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.code == "start")
            )
            plan = result.scalar_one()

        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        existing_sub = await get_active_subscription(session, db_user.id)
        if existing_sub:
            await renew_subscription(session, existing_sub.id, period_end, charge_id)
            sub = existing_sub
        else:
            sub = await create_subscription(session, db_user.id, plan.id, charge_id, period_end)

        amount = Decimal(str(payment.total_amount))
        is_first = not bool(payment.is_first_recurring) if hasattr(payment, "is_first_recurring") else True

        await record_payment(
            session=session,
            user_id=db_user.id,
            subscription_id=sub.id,
            charge_id=charge_id,
            amount=amount,
            is_first_recurring=is_first,
        )

        await session.commit()

    await message.answer(
        f"Подписка {plan.title} активирована!\n"
        f"- До {plan.max_products} товаров\n"
        f"- Действует до {period_end.strftime('%d.%m.%Y')}\n\n"
        f"Добавляйте товары командой /add"
    )
    logger.info("Payment processed for user %s, plan %s, charge %s", db_user.id, plan.code, charge_id)
