import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import PreCheckoutQuery

from pricemonitorbot.config import settings
from pricemonitorbot.bot.handlers.add import router as add_router
from pricemonitorbot.bot.handlers.list_remove import router as list_remove_router
from pricemonitorbot.bot.handlers.start import router as start_router
from pricemonitorbot.bot.handlers.status import router as status_router
from pricemonitorbot.bot.handlers.subscribe import router as subscribe_router
from pricemonitorbot.bot.middlewares import UserMiddleware
from pricemonitorbot.payments.stars import router as payments_router

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    @dp.pre_checkout_query()
    async def on_pre_checkout(query: PreCheckoutQuery) -> None:
        await query.answer(ok=True)

    dp.include_router(start_router)
    dp.include_router(add_router)
    dp.include_router(list_remove_router)
    dp.include_router(subscribe_router)
    dp.include_router(status_router)
    dp.include_router(payments_router)

    return bot, dp
