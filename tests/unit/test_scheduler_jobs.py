from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pricemonitorbot.parsers.base import ParseResult


@pytest.mark.asyncio
class TestCheckWildberriesProducts:
    async def test_price_change_triggers_notification(self):
        from pricemonitorbot.scheduler.jobs import check_wildberries_products

        product = MagicMock()
        product.id = 1
        product.external_id = "123456789"
        product.title = "Test Product"
        product.last_price = Decimal("100.00")
        product.last_in_stock = True
        product.user_id = 1

        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [product]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_bot = AsyncMock()

        with (
            patch("pricemonitorbot.scheduler.jobs.async_session_factory") as mock_factory,
            patch("pricemonitorbot.scheduler.jobs.WildberriesParser") as mock_parser_cls,
            patch("pricemonitorbot.scheduler.jobs.send_price_change_notification") as mock_notify,
            patch("pricemonitorbot.scheduler.jobs._get_user_telegram_id", return_value=12345),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_parser = AsyncMock()
            mock_parser.fetch.return_value = ParseResult(
                price=Decimal("150.00"), in_stock=True, title="Test Product"
            )
            mock_parser_cls.return_value = mock_parser

            mock_notify.return_value = None

            await check_wildberries_products(mock_bot)

            mock_notify.assert_called_once()
            call_kwargs = mock_notify.call_args
            assert call_kwargs[1]["old_price"] == Decimal("100.00")
            assert call_kwargs[1]["new_price"] == Decimal("150.00")

    async def test_no_change_no_notification(self):
        from pricemonitorbot.scheduler.jobs import check_wildberries_products

        product = MagicMock()
        product.id = 1
        product.external_id = "123456789"
        product.title = "Test Product"
        product.last_price = Decimal("100.00")
        product.last_in_stock = True
        product.user_id = 1

        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [product]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        mock_bot = AsyncMock()

        with (
            patch("pricemonitorbot.scheduler.jobs.async_session_factory") as mock_factory,
            patch("pricemonitorbot.scheduler.jobs.WildberriesParser") as mock_parser_cls,
            patch("pricemonitorbot.scheduler.jobs.send_price_change_notification") as mock_notify,
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_parser = AsyncMock()
            mock_parser.fetch.return_value = ParseResult(
                price=Decimal("100.00"), in_stock=True, title="Test Product"
            )
            mock_parser_cls.return_value = mock_parser

            await check_wildberries_products(mock_bot)

            mock_notify.assert_not_called()

    async def test_error_on_one_product_others_continue(self):
        from pricemonitorbot.scheduler.jobs import check_wildberries_products

        product_ok = MagicMock()
        product_ok.id = 1
        product_ok.external_id = "111"
        product_ok.title = "OK Product"
        product_ok.last_price = Decimal("100.00")
        product_ok.last_in_stock = True
        product_ok.user_id = 1

        product_err = MagicMock()
        product_err.id = 2
        product_err.external_id = "999"
        product_err.title = "Bad Product"
        product_err.last_price = Decimal("50.00")
        product_err.last_in_stock = True
        product_err.user_id = 1

        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [product_err, product_ok]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_bot = AsyncMock()

        with (
            patch("pricemonitorbot.scheduler.jobs.async_session_factory") as mock_factory,
            patch("pricemonitorbot.scheduler.jobs.WildberriesParser") as mock_parser_cls,
            patch("pricemonitorbot.scheduler.jobs.send_price_change_notification") as mock_notify,
            patch("pricemonitorbot.scheduler.jobs._get_user_telegram_id", return_value=12345),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_parser = AsyncMock()

            def fetch_side_effect(sku):
                if sku == "999":
                    return ParseResult(error="timeout")
                return ParseResult(price=Decimal("200.00"), in_stock=True, title="OK Product")

            mock_parser.fetch.side_effect = fetch_side_effect
            mock_parser_cls.return_value = mock_parser
            mock_notify.return_value = None

            await check_wildberries_products(mock_bot)

            mock_notify.assert_called_once()
