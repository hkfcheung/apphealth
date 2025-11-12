"""Base parser interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models import StatusType


class BaseParser(ABC):
    """Base class for all parsers."""

    @abstractmethod
    async def parse(self, content: str, url: str) -> Dict[str, Any]:
        """
        Parse content and return structured data.

        Args:
            content: Raw content (HTML, XML, JSON string)
            url: Source URL

        Returns:
            Dict with keys:
                - status: StatusType
                - summary: str
                - raw_data: dict (original parsed data)
                - last_changed_at: datetime or None
        """
        pass

    @abstractmethod
    def can_parse(self, content_type: str, content: str) -> bool:
        """
        Check if this parser can handle the content.

        Args:
            content_type: HTTP Content-Type header
            content: Raw content

        Returns:
            True if parser can handle this content
        """
        pass
