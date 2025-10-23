"""Parser factory and utilities."""
from typing import Dict, Any, Optional
import httpx
from app.parsers.json_parser import JSONParser
from app.parsers.rss_parser import RSSParser
from app.parsers.html_parser import HTMLParser
from app.models import ParserType, StatusType
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating and using appropriate parsers."""

    def __init__(self):
        self.parsers = [
            JSONParser(),
            RSSParser(),
            HTMLParser(),
        ]

    async def parse_url(
        self,
        url: str,
        parser_type: ParserType = ParserType.AUTO,
        use_playwright: bool = False,
        auth_state_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch and parse a URL.

        Args:
            url: URL to fetch
            parser_type: Preferred parser type
            use_playwright: Use Playwright for dynamic content
            auth_state_file: Path to saved authentication state (for authenticated sessions)

        Returns:
            Dict with status, summary, raw_data, last_changed_at, source_type
        """
        try:
            # Fetch content
            if use_playwright:
                content, content_type = await self._fetch_with_playwright(url, auth_state_file)
            else:
                content, content_type = await self._fetch_with_httpx(url)

            # Determine parser
            if parser_type == ParserType.AUTO:
                parser = self._auto_select_parser(content_type, content)
            else:
                parser = self._get_parser_by_type(parser_type)

            if not parser:
                raise ValueError(f"No suitable parser found for {url}")

            # Parse content
            result = await parser.parse(content, url)

            # Add source type
            source_type = self._get_source_type(parser)
            result["source_type"] = source_type

            logger.info(f"Successfully parsed {url} using {source_type} parser: {result['status']}")
            return result

        except Exception as e:
            logger.error(f"Failed to parse {url}: {e}")
            return {
                "status": StatusType.UNKNOWN,
                "summary": f"Error: {str(e)}",
                "raw_data": {},
                "last_changed_at": None,
                "source_type": "error",
                "error": str(e),
            }

    async def _fetch_with_httpx(self, url: str) -> tuple[str, str]:
        """Fetch URL using httpx."""
        headers = {
            "User-Agent": settings.user_agent,
            "Accept": "text/html,application/json,application/xml,application/rss+xml",
        }

        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return response.text, content_type

    async def _fetch_with_playwright(self, url: str, auth_state_file: Optional[str] = None) -> tuple[str, str]:
        """Fetch URL using Playwright (for dynamic pages)."""
        from playwright.async_api import async_playwright
        import os

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # Create context with saved authentication if available
            context_options = {}
            if auth_state_file and os.path.exists(auth_state_file):
                logger.info(f"Loading authentication state from {auth_state_file}")
                context_options["storage_state"] = auth_state_file

            context = await browser.new_context(**context_options)
            page = await context.new_page()
            page.set_default_timeout(settings.request_timeout * 1000)

            await page.goto(url, wait_until="networkidle")

            # Wait a bit for any dynamic content to load
            import asyncio
            await asyncio.sleep(3)

            content = await page.content()
            await browser.close()

            return content, "text/html"

    def _auto_select_parser(self, content_type: str, content: str):
        """Automatically select appropriate parser."""
        for parser in self.parsers:
            if parser.can_parse(content_type, content):
                return parser
        return None

    def _get_parser_by_type(self, parser_type: ParserType):
        """Get parser by explicit type."""
        mapping = {
            ParserType.JSON: JSONParser,
            ParserType.RSS: RSSParser,
            ParserType.HTML: HTMLParser,
        }
        parser_class = mapping.get(parser_type)
        return parser_class() if parser_class else None

    def _get_source_type(self, parser) -> str:
        """Get source type string from parser."""
        if isinstance(parser, JSONParser):
            return "json"
        elif isinstance(parser, RSSParser):
            return "rss"
        elif isinstance(parser, HTMLParser):
            return "html"
        return "unknown"


# Global parser factory instance
parser_factory = ParserFactory()
