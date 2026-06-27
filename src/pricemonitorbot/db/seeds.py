import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pricemonitorbot.db.models import SubscriptionPlan

logger = logging.getLogger(__name__)

PLANS = [
    {"code": "start", "title": "Start", "max_products": 5, "price_stars": 149},
    {"code": "business", "title": "Business", "max_products": 25, "price_stars": 399},
    {"code": "pro", "title": "Pro", "max_products": 100, "price_stars": 899},
]


async def seed_subscription_plans(session: AsyncSession) -> None:
    for plan_data in PLANS:
        result = await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.code == plan_data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            plan = SubscriptionPlan(**plan_data, is_active=True)
            session.add(plan)
            logger.info("Seeded plan: %s", plan_data["code"])
        else:
            existing.title = plan_data["title"]
            existing.max_products = plan_data["max_products"]
            existing.price_stars = plan_data["price_stars"]
            existing.is_active = True

    await session.flush()
