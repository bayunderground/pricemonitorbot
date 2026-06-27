from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ParseResult:
    price: Decimal | None = None
    in_stock: bool = False
    title: str | None = None
    error: str | None = None


class ParserAdapter(ABC):
    @abstractmethod
    async def fetch(self, url_or_sku: str) -> ParseResult:
        ...
