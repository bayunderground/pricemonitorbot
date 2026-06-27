from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Добро пожаловать в PriceMonitorBot!\n\n"
        "Я отслеживаю цены и наличие товаров на Wildberries.\n"
        "Добавьте товар командой /add, и я буду присылать уведомления при изменениях.\n\n"
        "Команды:\n"
        "/add — добавить товар\n"
        "/list — мои товары\n"
        "/remove — удалить товар\n"
        "/subscribe — тарифы и подписка\n"
        "/status — статус подписки\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Команды бота:\n\n"
        "/add <ссылка или артикул> — добавить товар для отслеживания\n"
        "/list — показать список отслеживаемых товаров\n"
        "/remove — удалить товар из отслеживания\n"
        "/subscribe — выбрать тариф и оформить подписку\n"
        "/status — текущий тариф и лимиты\n"
        "/help — это сообщение"
    )
