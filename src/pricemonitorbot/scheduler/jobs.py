import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select

from pricemonitorbot.db.models import MarketplaceType, TrackedProduct, User
from pricemonitorbot.db.repositories.products import record_price_change, update_product_snapshot
from pricemonitorbot.db.session import async_session_factory
from pricemonitorbot.notifications.notifier import send_price_change_notification
from pricemonitorbot.parsers import WildberriesParser

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 5


async def check_wildberries_products(bot: Bot) -> None:
    logger.info("Starting WB product check job...")

    parser = WildberriesParser()

    async with async_session_factory() as session:
        result = await session.execute(
            select(TrackedProduct).where(
                TrackedProduct.marketplace == MarketplaceType.wildberries,
                TrackedProduct.is_active.is_(True),
            )
        )
        products = list(result.scalars().all())

    if not products:
        logger.info("No active WB products to check")
        return

    logger.info("Checking %d WB products", len(products))

    for product in products:
        try:
            await _check_single_product(bot, parser, product)
        except Exception:
            logger.exception("Error checking product %s (id=%s)", product.external_id, product.id)

        await asyncio.sleep(1)

    logger.info("WB product check job finished")


async def _check_single_product(bot: Bot, parser: WildberriesParser, product: TrackedProduct) -> None:
    result = None
    for attempt in range(1, MAX_RETRIES + 1):
        result = await parser.fetch(product.external_id)
        if result.error is None:
            break
        if attempt < MAX_RETRIES:
            logger.warning("Retry %d/%d for product %s: %s", attempt, MAX_RETRIES, product.external_id, result.error)
            await asyncio.sleep(RETRY_DELAY)

    if result is None or result.error:
        logger.error("Failed to parse product %s after %d attempts: %s", product.external_id, MAX_RETRIES, result.error if result else "no result")
        return

    price_changed = result.price != product.last_price
    stock_changed = result.in_stock != product.last_in_stock

    if not price_changed and not stock_changed:
        return

    logger.info("Change detected for %s: price %s->%s, stock %s->%s",
                product.external_id, product.last_price, result.price, product.last_in_stock, result.in_stock)

    old_price = product.last_price
    old_stock = product.last_in_stock

    async with async_session_factory() as session:
        await update_product_snapshot(session, product.id, result.price, result.in_stock)
        await record_price_change(session, product.id, result.price, result.in_stock)
        await session.commit()

    try:
        user_result = await _get_user_telegram_id(product.user_id)
        if user_result:
            await send_price_change_notification(
                bot=bot,
                chat_id=user_result,
                product_title=product.title,
                old_price=old_price,
                new_price=result.price,
                old_stock=old_stock,
                new_stock=result.in_stock,
            )
    except Exception:
        logger.exception("Failed to send notification for product %s", product.external_id)


async def _get_user_telegram_id(user_id: int) -> int | None:
    async with async_session_factory() as session:
        result = await session.execute(select(User.telegram_id).where(User.id == user_id))
        return result.scalar_one_or_none()
