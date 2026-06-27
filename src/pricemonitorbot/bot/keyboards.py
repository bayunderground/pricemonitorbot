from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def remove_product_keyboard(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        title = p.title or p.external_id
        if len(title) > 30:
            title = title[:27] + "..."
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"remove:{p.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
