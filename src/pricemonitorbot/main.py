import asyncio
import logging
import signal

from pricemonitorbot.bot import create_bot
from pricemonitorbot.config import settings
from pricemonitorbot.db.seeds import seed_subscription_plans
from pricemonitorbot.db.session import async_session_factory
from pricemonitorbot.logging_config import setup_logging
from pricemonitorbot.scheduler import create_scheduler
from pricemonitorbot.scheduler.jobs import check_wildberries_products

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("PriceMonitorBot starting...")

    async with async_session_factory() as session:
        await seed_subscription_plans(session)
        await session.commit()
    logger.info("Subscription plans seeded")

    bot, dp = create_bot()
    scheduler = create_scheduler()

    scheduler.add_job(
        check_wildberries_products,
        "interval",
        hours=settings.WB_PARSE_INTERVAL_HOURS,
        args=[bot],
        id="wb_product_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started, WB check interval: %dh", settings.WB_PARSE_INTERVAL_HOURS)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(bot, dp, scheduler)))

    logger.info("Starting long polling...")
    await dp.start_polling(bot)


async def _shutdown(bot, dp, scheduler) -> None:
    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)
    await bot.session.close()
    await dp.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
