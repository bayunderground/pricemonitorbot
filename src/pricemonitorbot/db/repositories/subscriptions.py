from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pricemonitorbot.db.models import Subscription, SubscriptionPlan, SubscriptionStatus


async def get_active_subscription(
    session: AsyncSession,
    user_id: int,
) -> Subscription | None:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.current_period_end > now,
        )
    )
    return result.scalar_one_or_none()


async def create_subscription(
    session: AsyncSession,
    user_id: int,
    plan_id: int,
    charge_id: str,
    period_end: datetime,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        status=SubscriptionStatus.active,
        is_recurring=True,
        current_period_end=period_end,
        telegram_charge_id=charge_id,
    )
    session.add(sub)
    await session.flush()
    return sub


async def renew_subscription(
    session: AsyncSession,
    subscription_id: int,
    new_period_end: datetime,
    charge_id: str,
) -> None:
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.current_period_end = new_period_end
        sub.status = SubscriptionStatus.active
        sub.telegram_charge_id = charge_id


async def get_user_product_limit(
    session: AsyncSession,
    user_id: int,
) -> int:
    sub = await get_active_subscription(session, user_id)
    if sub is None:
        return 5

    result = await session.execute(
        select(SubscriptionPlan.max_products).where(SubscriptionPlan.id == sub.plan_id)
    )
    limit = result.scalar_one_or_none()
    return limit if limit is not None else 5


async def is_subscription_active(
    session: AsyncSession,
    user_id: int,
) -> bool:
    sub = await get_active_subscription(session, user_id)
    return sub is not None


async def get_all_active_subscriptions(
    session: AsyncSession,
) -> list[Subscription]:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.current_period_end > now,
        )
    )
    return list(result.scalars().all())
