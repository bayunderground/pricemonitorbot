from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pricemonitorbot.db.models import Payment


async def record_payment(
    session: AsyncSession,
    user_id: int,
    subscription_id: int,
    charge_id: str,
    amount: Decimal,
    is_first_recurring: bool,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        subscription_id=subscription_id,
        telegram_payment_charge_id=charge_id,
        amount_stars=amount,
        is_first_recurring=is_first_recurring,
    )
    session.add(payment)
    await session.flush()
    return payment


async def payment_exists(
    session: AsyncSession,
    charge_id: str,
) -> bool:
    result = await session.execute(
        select(Payment.id).where(Payment.telegram_payment_charge_id == charge_id)
    )
    return result.scalar_one_or_none() is not None
