from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from pricemonitorbot.db.models import MarketplaceType, TrackedProduct


async def add_product(
    session: AsyncSession,
    user_id: int,
    marketplace: MarketplaceType,
    external_id: str,
    url: str | None,
    title: str | None,
    price: Decimal | None,
    in_stock: bool,
) -> TrackedProduct:
    product = TrackedProduct(
        user_id=user_id,
        marketplace=marketplace,
        external_id=external_id,
        url=url,
        title=title,
        last_price=price,
        last_in_stock=in_stock,
    )
    session.add(product)
    await session.flush()
    return product


async def get_user_products(
    session: AsyncSession,
    user_id: int,
) -> list[TrackedProduct]:
    result = await session.execute(
        select(TrackedProduct)
        .where(TrackedProduct.user_id == user_id, TrackedProduct.is_active.is_(True))
        .order_by(TrackedProduct.created_at.desc())
    )
    return list(result.scalars().all())


async def remove_product(
    session: AsyncSession,
    product_id: int,
    user_id: int,
) -> bool:
    result = await session.execute(
        select(TrackedProduct).where(
            TrackedProduct.id == product_id,
            TrackedProduct.user_id == user_id,
            TrackedProduct.is_active.is_(True),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        return False
    product.is_active = False
    return True


async def count_user_products(
    session: AsyncSession,
    user_id: int,
) -> int:
    result = await session.execute(
        select(func.count()).where(
            TrackedProduct.user_id == user_id,
            TrackedProduct.is_active.is_(True),
        )
    )
    return result.scalar_one()


async def get_product_by_external_id(
    session: AsyncSession,
    user_id: int,
    external_id: str,
) -> TrackedProduct | None:
    result = await session.execute(
        select(TrackedProduct).where(
            TrackedProduct.user_id == user_id,
            TrackedProduct.external_id == external_id,
            TrackedProduct.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_product_snapshot(
    session: AsyncSession,
    product_id: int,
    price: Decimal | None,
    in_stock: bool,
) -> None:
    result = await session.execute(
        select(TrackedProduct).where(TrackedProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product:
        product.last_price = price
        product.last_in_stock = in_stock


async def record_price_change(
    session: AsyncSession,
    product_id: int,
    price: Decimal | None,
    in_stock: bool,
) -> None:
    from pricemonitorbot.db.models import PriceHistory

    entry = PriceHistory(product_id=product_id, price=price, in_stock=in_stock)
    session.add(entry)
