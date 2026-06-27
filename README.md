# PriceMonitorBot

Telegram-бот для отслеживания цен и наличия товаров на Wildberries.

## Установка

### Требования
- Python 3.12+
- PostgreSQL 14+

### Настройка

```bash
# Клонировать репозиторий
git clone https://github.com/bayunderground/pricemonitorbot.git
cd pricemonitorbot

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Заполнить .env: BOT_TOKEN, DATABASE_URL

# Применить миграции
PYTHONPATH=src alembic upgrade head

# Запустить бота
PYTHONPATH=src python -m pricemonitorbot.main
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен Telegram-бота от @BotFather | — |
| `DATABASE_URL` | URL подключения к PostgreSQL (asyncpg) | — |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `SCHEDULER_TIMEZONE` | Часовой пояс планировщика | `Europe/Moscow` |
| `WB_PARSE_INTERVAL_HOURS` | Интервал проверки товаров WB (часы) | `1` |
| `ADMIN_CHAT_ID` | Telegram ID для алертов админа | — |

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие и краткая инструкция |
| `/help` | Список команд |
| `/add <ссылка или артикул>` | Добавить товар для отслеживания |
| `/list` | Показать отслеживаемые товары |
| `/remove` | Удалить товар из отслеживания |
| `/subscribe` | Выбрать тариф и оформить подписку |
| `/status` | Текущий тариф и лимиты |

## Деплой на VPS

```bash
# Установить systemd-сервис
sudo cp deploy/pricemonitorbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pricemonitorbot
sudo systemctl start pricemonitorbot

# Проверить статус
sudo systemctl status pricemonitorbot

# Логи
sudo journalctl -u pricemonitorbot -f
```

## Тесты

```bash
PYTHONPATH=src python -m pytest tests/unit/ -v
```

## Линтинг

```bash
ruff check src/ tests/
black --check src/ tests/
```
