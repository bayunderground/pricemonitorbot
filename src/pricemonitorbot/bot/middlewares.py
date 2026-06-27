import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from pricemonitorbot.db.repositories.user_repo import get_or_create_user
from pricemonitorbot.db.session import get_session

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            return await handler(event, data)

        if user is None:
            return await handler(event, data)

        async with get_session() as session:
            db_user = await get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
            )
            data["db_user"] = db_user

        return await handler(event, data)
