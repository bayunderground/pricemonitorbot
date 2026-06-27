import logging
import re
from decimal import Decimal

import httpx

from pricemonitorbot.parsers.base import ParserAdapter, ParseResult

logger = logging.getLogger(__name__)

WB_API_URL = "https://card.wb.ru/cards/v2/detail"
WB_DEFAULT_PARAMS = {
    "appType": "1",
    "curr": "rub",
    "dest": "-1257786",
    "spp": "30",
}

SKU_PATTERNS = [
    re.compile(r"/catalog/(\d+)"),
    re.compile(r"/detail\.aspx\?id=(\d+)"),
    re.compile(r"/product/[^/]+-(\d+)"),
]


def normalize_wb_input(raw: str) -> str | None:
    raw = raw.strip()
    for pattern in SKU_PATTERNS:
        match = pattern.search(raw)
        if match:
            return match.group(1)
    if raw.isdigit():
        return raw
    return None


class WildberriesParser(ParserAdapter):
    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout

    async def fetch(self, url_or_sku: str) -> ParseResult:
        sku = normalize_wb_input(url_or_sku)
        if not sku:
            return ParseResult(error=f"Не удалось извлечь артикул из: {url_or_sku}")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                params = {**WB_DEFAULT_PARAMS, "nm": sku}
                response = await client.get(WB_API_URL, params=params)

                if response.status_code == 404:
                    return ParseResult(error=f"Товар {sku} не найден")
                response.raise_for_status()

                data = response.json()
                return self._parse_response(data, sku)

        except httpx.TimeoutException:
            return ParseResult(error=f"Таймаут при запросе товара {sku}")
        except httpx.HTTPStatusError as e:
            return ParseResult(error=f"HTTP ошибка {e.response.status_code} для товара {sku}")
        except Exception as e:
            logger.exception("Unexpected error parsing WB sku %s", sku)
            return ParseResult(error=f"Ошибка парсинга товара {sku}: {e}")

    def _parse_response(self, data: dict, sku: str) -> ParseResult:
        try:
            products = data.get("data", {}).get("products", [])
            if not products:
                return ParseResult(error=f"Товар {sku} не найден в ответе API")

            product = products[0]
            title = product.get("name")

            price = None
            sale_price = product.get("salePriceU") or product.get("totalSalePriceU")
            if sale_price is not None:
                price = Decimal(str(sale_price)) / Decimal("100")

            in_stock = False
            sizes = product.get("sizes", [])
            for size in sizes:
                stocks = size.get("stocks", [])
                for stock in stocks:
                    if stock.get("qty", 0) > 0:
                        in_stock = True
                        break
                if in_stock:
                    break

            return ParseResult(price=price, in_stock=in_stock, title=title)

        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse WB response for sku %s: %s", sku, e)
            return ParseResult(error=f"Неожиданная структура ответа для товара {sku}")
