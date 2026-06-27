# CLAUDE.md — PriceMonitorBot

Этот файл — контекст проекта для Claude Code. Читай его перед началом любой задачи в репозитории.

## О проекте

PriceMonitorBot — Telegram-бот для продавцов на Ozon и Wildberries. Отслеживает цены и наличие
товаров конкурентов по ссылке/артикулу и присылает уведомления при изменениях. Работает автономно:
пользователь добавляет товары командами, бот сам парсит по расписанию и шлёт алерты.

Целевая аудитория — владельцы и менеджеры малого бизнеса на Ozon/Wildberries.

MVP-команды: `/start`, `/help`, `/add`, `/list`, `/remove`, `/subscribe`, `/status`.

## Технологический стек и обоснование решений

| Компонент | Выбор | Почему |
|---|---|---|
| Язык | Python 3.12+ | требование |
| Telegram-бот | aiogram 3.x | актуальный async-фреймворк, нативная поддержка Stars-инвойсов |
| Парсинг WB | httpx + внутренние JSON-эндпоинты витрины | данные отдаются без JS-рендеринга, html-парсинг избыточен |
| Парсинг Ozon | Playwright (headless Chromium) + playwright-stealth | контент грузится динамически через JS, обычный HTTP-клиент не получает цену без рендеринга страницы |
| БД | PostgreSQL | требование, сразу боевая |
| Планировщик | APScheduler (`AsyncIOScheduler` + `SQLAlchemyJobStore` на той же Postgres) | работает в одном event loop с ботом, задачи переживают рестарт процесса (jobstore в БД), не нужен отдельный cron-процесс с своим подключением к БД; добавление товара через `/add` можно сразу поставить в очередь без правки cron-файлов. Минус — чуть больше связности с процессом бота, но для MVP это приемлемо |
| Управление зависимостями | `requirements.txt` + venv | проще poetry для деплоя на голый VPS, меньше движущихся частей на старте |
| Деплой | Без Docker, кроме Ozon-парсера | Бот, планировщик, WB-парсер и PostgreSQL ставятся напрямую на VPS (venv + systemd-сервис, нативный PostgreSQL) — меньше слоёв абстракции для основной части системы. **Docker используется точечно — только для модуля с Playwright/Chromium**, потому что именно у него тяжёлые и хрупкие системные зависимости (браузерные библиотеки), которые удобнее изолировать в контейнере, не затрагивая остальной хост |
| Миграции | Alembic | стандарт для SQLAlchemy-проектов |

## Структура репозитория

```
pricemonitorbot/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── deploy/
│   └── pricemonitorbot.service       # systemd-юнит для бота (без Docker)
├── services/
│   └── ozon-parser-service/          # единственная часть проекта, которая живёт в Docker
│       ├── Dockerfile                # headless Chromium + Playwright + playwright-stealth
│       ├── docker-compose.yml        # удобный запуск/рестарт контейнера локально и на VPS
│       ├── requirements.txt
│       └── app.py                    # лёгкий HTTP-сервис (FastAPI): принимает url/sku, отдаёт price/in_stock
├── alembic/
│   └── versions/
├── src/
│   └── pricemonitorbot/
│       ├── main.py                 # точка входа
│       ├── config.py                # настройки из env (pydantic-settings)
│       ├── bot/
│       │   ├── handlers/
│       │   │   ├── start.py
│       │   │   ├── add.py
│       │   │   ├── list_remove.py
│       │   │   ├── subscribe.py
│       │   │   └── status.py
│       │   ├── keyboards.py
│       │   └── middlewares.py       # проверка подписки/лимитов
│       ├── parsers/
│       │   ├── base.py              # абстрактный ParserAdapter
│       │   ├── ozon.py              # HTTP-клиент к ozon-parser-service (сам Playwright здесь не живёт)
│       │   └── wildberries.py       # обычный httpx, работает в основном процессе без Docker
│       ├── scheduler/
│       │   └── jobs.py
│       ├── payments/
│       │   └── stars.py             # createInvoiceLink, обработка successful_payment
│       ├── db/
│       │   ├── models.py
│       │   ├── session.py
│       │   └── repositories/
│       └── notifications/
│           └── notifier.py
└── tests/
    ├── unit/
    └── integration/
    └── fixtures/                    # сохранённые HTML/JSON-снэпшоты карточек товаров
```

## Конвенции кода

- Везде `async`/`await`, синхронный код в бизнес-логике не используется.
- Форматирование — `black`, линт — `ruff`. Прогонять перед коммитом.
- Типизация обязательна (`mypy` в CI желателен, но не блокирует MVP).
- Конфигурация — только через переменные окружения (`pydantic-settings`), никаких хардкод-секретов.
- Каждый адаптер парсера реализует единый интерфейс `ParserAdapter.fetch(url_or_sku) -> ParseResult`
  (`price: Decimal | None`, `in_stock: bool`, `title: str | None`, `error: str | None`).
  Ошибка одного товара не должна ронять обход остальных в job'е планировщика.
- Любая денежная величина — `Decimal`, не `float`.

## Схема БД (ключевые таблицы)

- **users** — `id`, `telegram_id`, `username`, `created_at`
- **subscription_plans** — `id`, `code`, `title`, `max_products`, `price_stars`, `is_active`
- **subscriptions** — `id`, `user_id`, `plan_id`, `status` (active/expired/canceled),
  `is_recurring`, `current_period_end`, `telegram_charge_id`
- **payments** — `id`, `user_id`, `subscription_id`, `telegram_payment_charge_id` (unique),
  `amount_stars`, `is_first_recurring`, `created_at` — лог транзакций, нужен для идемпотентности
  обработки `successful_payment` и для `refundStarPayment`
- **tracked_products** — `id`, `user_id`, `marketplace` (`ozon`/`wildberries`), `external_id`,
  `url`, `title`, `last_price`, `last_in_stock`, `is_active`, `created_at`
- **price_history** — `id`, `product_id`, `price`, `in_stock`, `checked_at`

## Важные ограничения — не нарушать без явного решения пользователя

### Монетизация
Только Telegram Stars (`XTR`). **Никакого YooKassa/CloudPayments/Qiwi/Robokassa и других внешних
эквайрингов на этом этапе** — сознательное ограничение MVP.

Тарифная сетка (предложена, можно скорректировать по марже — конечная цена в рублях для
пользователя зависит от способа покупки звёзд и платформенных комиссий, сверить перед запуском):

| Тариф | Лимит товаров | Цена |
|---|---|---|
| Start | до 5 | 149 ⭐/мес |
| Business | до 25 | 399 ⭐/мес |
| Pro | до 100 | 899 ⭐/мес |

### Telegram Stars API — проверено по актуальной документации (core.telegram.org/bots/api)
- `subscription_period` в `createInvoiceLink` сейчас принимает **только 2592000 секунд (30 дней)**.
  Других периодов нет — нельзя сделать «квартальную» подписку нативно через Stars.
- Максимальная цена подписки — 10000 Stars (наша сетка укладывается с запасом).
- `provider_token` для Stars-платежей — пустая строка.
- Слушать `successful_payment`: поля `is_recurring`, `is_first_recurring`,
  `subscription_expiration_date`. Сохранять `telegram_payment_charge_id` в `payments` —
  понадобится для `refundStarPayment`.
- Отмена/управление подпиской со стороны бота — `editUserStarSubscription`.
- Перед реализацией платёжного модуля **свериться с актуальной документацией** ещё раз —
  раздел Payments менялся несколько раз за последний год.

### Парсинг
- У Ozon и Wildberries **нет официального API для цен/наличия чужих товаров** — Seller API
  даёт доступ только к собственному каталогу продавца. Парсинг публичных страниц — единственный
  путь, ограничений на этом архитектура не меняет.
- Ozon: обязательна браузерная автоматизация (Playwright). Реализовать **anti-detect с первого
  спринта** (playwright-stealth, реалистичные UA/viewport, паузы между действиями).
  **Ротация прокси — осознанно не делаем в MVP**, при необходимости добавим отдельным этапом
  после оценки реальной частоты блокировок в проде.
- Ozon-парсер живёт в `services/ozon-parser-service/` как отдельный HTTP-сервис в Docker-контейнере
  (FastAPI + Playwright). `parsers/ozon.py` в основном процессе — просто HTTP-клиент к нему.
  Это единственное место в проекте, где используется Docker — вынесено туда из-за тяжёлых и
  хрупких системных зависимостей Chromium. Бот, планировщик, WB-парсер и PostgreSQL Docker не
  используют, работают напрямую на хосте.
- Wildberries: обычно достаточно httpx к внутренним JSON-эндпоинтам, без браузера.
- **Если парсер натыкается на капчу/блокировку — детектируем и пропускаем итерацию с логом
  ошибки. Не реализуем обход капчи.** Это принципиальное ограничение, а не временная мера.
- Частота опроса: WB можно чаще (например, раз в час), Ozon — реже (например, раз в день) из-за
  большей ресурсоёмкости headless-браузера и риска блокировок.
- Уважать разумную нагрузку на маркетплейсы — не параллелить сотни запросов одновременно.

## Переменные окружения (`.env`)

```
BOT_TOKEN=
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pricemonitorbot
OZON_PARSER_SERVICE_URL=http://localhost:8001
LOG_LEVEL=INFO
SCHEDULER_TIMEZONE=Europe/Moscow
OZON_PARSE_INTERVAL_HOURS=24
WB_PARSE_INTERVAL_HOURS=1
```

## Команды

```bash
# Разработка
# PostgreSQL устанавливается нативно (apt install postgresql / локальный сервис), Docker для него не используется
pip install -r requirements.txt
alembic upgrade head                          # применить миграции
python -m pricemonitorbot.main                # запустить бота (long polling)

# Ozon-парсер (единственная часть на Docker) — поднимается отдельно при работе с Ozon
docker compose -f services/ozon-parser-service/docker-compose.yml up -d --build

# Тесты
pytest tests/unit                              # без сетевых вызовов, на фикстурах
pytest tests/integration                       # требует поднятой тестовой БД

# Линт/форматирование
ruff check . && black --check .

# Миграции
alembic revision --autogenerate -m "описание"
alembic upgrade head

# Деплой (VPS, после получения доступов)
# Бот: systemd-сервис (deploy/pricemonitorbot.service), без Docker
sudo systemctl restart pricemonitorbot
sudo systemctl status pricemonitorbot
# Ozon-парсер: единственный компонент, который пересобирается/перезапускается через Docker
docker compose -f services/ozon-parser-service/docker-compose.yml up -d --build
```

## Тестирование парсеров

Никаких живых обращений к Ozon/WB в CI — нестабильно и риск блокировки IP CI-раннера.
Тесты парсеров работают на сохранённых HTML/JSON-снэпшотах в `tests/fixtures/`. Снэпшоты
обновляются вручную при изменении вёрстки/структуры эндпоинтов маркетплейса.

## Открытые вопросы для последующих этапов (не блокируют MVP)

- Точная калибровка тарифов в рублёвом эквиваленте под актуальный курс Stars.
- Нужен ли бесплатный trial-период — пока не закладываем в схему, легко добавить отдельным полем
  в `subscriptions` при необходимости.
- Эндпоинты WB могут меняться без предупреждения — закладывать мониторинг падения парсера
  (например, алерт админу при N подряд неудачных парсингах).
