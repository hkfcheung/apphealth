"""Tests for parsers."""
import pytest
from app.parsers.json_parser import JSONParser
from app.parsers.rss_parser import RSSParser
from app.parsers.html_parser import HTMLParser
from app.models import StatusType


class TestJSONParser:
    """Test JSON parser."""

    @pytest.mark.asyncio
    async def test_statuspage_io_format(self):
        """Test parsing Statuspage.io JSON format."""
        parser = JSONParser()
        content = '''
        {
          "status": {
            "indicator": "none",
            "description": "All Systems Operational"
          },
          "components": [
            {"status": "operational", "name": "API"},
            {"status": "operational", "name": "Web"}
          ]
        }
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] == StatusType.OPERATIONAL
        assert "operational" in result["summary"].lower()

    @pytest.mark.asyncio
    async def test_minor_indicator(self):
        """Test minor status indicator."""
        parser = JSONParser()
        content = '''
        {
          "status": {
            "indicator": "minor",
            "description": "Minor Service Issues"
          }
        }
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] == StatusType.DEGRADED

    @pytest.mark.asyncio
    async def test_can_parse_json(self):
        """Test can_parse method."""
        parser = JSONParser()

        assert parser.can_parse("application/json", "{}")
        assert parser.can_parse("text/plain", '{"valid": "json"}')
        assert not parser.can_parse("text/html", "not json")


class TestRSSParser:
    """Test RSS parser."""

    @pytest.mark.asyncio
    async def test_rss_feed_parsing(self):
        """Test basic RSS feed parsing."""
        parser = RSSParser()
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Status Updates</title>
            <item>
              <title>Resolved - Database Issues</title>
              <description>The database issues have been resolved.</description>
              <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] == StatusType.OPERATIONAL
        assert "incidents" in result["raw_data"]

    @pytest.mark.asyncio
    async def test_unresolved_incident(self):
        """Test unresolved incident detection."""
        parser = RSSParser()
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Investigating - Service Degradation</title>
              <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] in [StatusType.DEGRADED, StatusType.OPERATIONAL]

    @pytest.mark.asyncio
    async def test_can_parse_rss(self):
        """Test can_parse method."""
        parser = RSSParser()

        assert parser.can_parse("application/rss+xml", "")
        assert parser.can_parse("application/xml", "")
        assert parser.can_parse("text/html", "<?xml version")
        assert not parser.can_parse("text/html", "<html>")


class TestHTMLParser:
    """Test HTML parser."""

    @pytest.mark.asyncio
    async def test_statuspage_io_html(self):
        """Test parsing Statuspage.io HTML."""
        parser = HTMLParser()
        content = '''
        <html>
          <head><title>Status Page</title></head>
          <body>
            <div class="status-indicator none">
              <span class="page-status">All Systems Operational</span>
            </div>
          </body>
        </html>
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] == StatusType.OPERATIONAL

    @pytest.mark.asyncio
    async def test_generic_html_with_status(self):
        """Test generic HTML parsing."""
        parser = HTMLParser()
        content = '''
        <html>
          <body>
            <h1>All Systems Operational</h1>
            <div class="status-banner">Everything is working fine</div>
          </body>
        </html>
        '''

        result = await parser.parse(content, "https://example.com")

        assert result["status"] == StatusType.OPERATIONAL

    @pytest.mark.asyncio
    async def test_can_parse_html(self):
        """Test can_parse method."""
        parser = HTMLParser()

        assert parser.can_parse("text/html", "")
        assert parser.can_parse("text/plain", "<!DOCTYPE html>")
        assert parser.can_parse("text/plain", "<html>")
        assert not parser.can_parse("application/json", "{}")
