import logging

from aiogram import Bot

from pricemonitorbot.config import settings

logger = logging.getLogger(__name__)


async def send_admin_alert(bot: Bot, message: str) -> None:
    if not settings.ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID not set, alert not sent: %s", message)
        return

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=f"⚠️ PriceMonitorBot Alert:\n\n{message}",
        )
    except Exception:
        logger.exception("Failed to send admin alert")
