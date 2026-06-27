import logging
from decimal import Decimal

from aiogram import Bot

logger = logging.getLogger(__name__)


def _format_price(price: Decimal | None) -> str:
    if price is None:
        return "—"
    return f"{price:.2f} ₽"


async def send_price_change_notification(
    bot: Bot,
    chat_id: int,
    product_title: str,
    old_price: Decimal | None,
    new_price: Decimal | None,
    old_stock: bool,
    new_stock: bool,
) -> None:
    title = product_title or "Товар"

    lines = [f"🔔 Изменение по товару: {title}\n"]

    if old_price != new_price:
        lines.append(f"💰 Цена: {_format_price(old_price)} → {_format_price(new_price)}")

    if old_stock != new_stock:
        old_str = "в наличии" if old_stock else "нет в наличии"
        new_str = "в наличии" if new_stock else "нет в наличии"
        lines.append(f"📊 Наличие: {old_str} → {new_str}")

    if len(lines) == 1:
        return

    await bot.send_message(chat_id, "\n".join(lines))
