"""DownDetector utility - provides links to DownDetector status pages.

Note: DownDetector uses Cloudflare protection that prevents automated scraping.
This module provides URL validation and link generation only.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def validate_downdetector_url(url: str) -> bool:
    """
    Validate that a URL is a valid DownDetector URL.

    Args:
        url: URL to validate

    Returns:
        True if valid DownDetector URL, False otherwise
    """
    if not url:
        return False

    return 'downdetector.com' in url.lower()
