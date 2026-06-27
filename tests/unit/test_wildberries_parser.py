import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pricemonitorbot.parsers.wildberries import WildberriesParser, normalize_wb_input

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def parser():
    return WildberriesParser()


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def make_response(status_code: int, json_data: dict | None = None, raise_error: bool = False):
    response = MagicMock()
    response.status_code = status_code
    if json_data is not None:
        response.json.return_value = json_data
    if raise_error:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class TestNormalizeInput:
    def test_bare_sku(self):
        assert normalize_wb_input("123456789") == "123456789"

    def test_bare_sku_with_spaces(self):
        assert normalize_wb_input("  123456789  ") == "123456789"

    def test_wb_catalog_url(self):
        assert normalize_wb_input("https://www.wildberries.ru/catalog/123456789/detail.aspx") == "123456789"

    def test_wb_detail_url(self):
        assert normalize_wb_input("https://www.wildberries.ru/detail.aspx?id=123456789") == "123456789"

    def test_wb_product_url(self):
        assert normalize_wb_input("https://www.wildberries.ru/product/futbolka-123456789") == "123456789"

    def test_invalid_input(self):
        assert normalize_wb_input("not a sku") is None

    def test_empty_string(self):
        assert normalize_wb_input("") is None


@pytest.mark.asyncio
class TestWildberriesParser:
    async def test_valid_product(self, parser):
        fixture = load_fixture("wb_product_ok.json")
        response = make_response(200, fixture)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            result = await parser.fetch("123456789")

        assert result.price == Decimal("1299.00")
        assert result.in_stock is True
        assert result.title == "Футболка мужская хлопок базовая"
        assert result.error is None

    async def test_out_of_stock(self, parser):
        fixture = load_fixture("wb_product_out_of_stock.json")
        response = make_response(200, fixture)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            result = await parser.fetch("987654321")

        assert result.price == Decimal("5499.00")
        assert result.in_stock is False
        assert result.title == "Куртка зимняя женская"
        assert result.error is None

    async def test_not_found(self, parser):
        fixture = load_fixture("wb_product_not_found.json")
        response = make_response(200, fixture)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            result = await parser.fetch("999999999")

        assert result.error is not None
        assert "не найден" in result.error

    async def test_timeout(self, parser):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            result = await parser.fetch("123456789")

        assert result.error is not None
        assert "Таймаут" in result.error

    async def test_invalid_sku(self, parser):
        result = await parser.fetch("not-a-sku")
        assert result.error is not None
        assert "Не удалось" in result.error

    async def test_http_error(self, parser):
        response = make_response(500, raise_error=True)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            result = await parser.fetch("123456789")

        assert result.error is not None

    async def test_url_input(self, parser):
        fixture = load_fixture("wb_product_ok.json")
        response = make_response(200, fixture)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            result = await parser.fetch("https://www.wildberries.ru/catalog/123456789/detail.aspx")

        assert result.error is None
        assert result.price == Decimal("1299.00")
