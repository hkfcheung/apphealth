"""RSS/Atom feed parser."""
import feedparser
import re
from datetime import datetime
from typing import Dict, Any
from app.parsers.base import BaseParser
from app.models import StatusType
from app.utils.normalizer import normalize_status, extract_summary
import logging

logger = logging.getLogger(__name__)


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean = clean.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    clean = clean.replace('&quot;', '"').replace('&apos;', "'")
    clean = clean.replace('&nbsp;', ' ')
    return clean.strip()


class RSSParser(BaseParser):
    """Parser for RSS/Atom status feeds."""

    def can_parse(self, content_type: str, content: str) -> bool:
        """Check if content is RSS/Atom."""
        if any(x in content_type.lower() for x in ["xml", "rss", "atom"]):
            return True
        # Try to detect XML
        if content.strip().startswith("<?xml") or "<rss" in content[:200] or "<feed" in content[:200]:
            return True
        return False

    async def parse(self, content: str, url: str) -> Dict[str, Any]:
        """Parse RSS/Atom feed."""
        try:
            feed = feedparser.parse(content)

            if feed.bozo and not feed.entries:
                raise ValueError(f"Invalid feed: {feed.get('bozo_exception', 'Unknown error')}")

            # Extract incidents from entries
            incidents = []
            latest_incident = None

            for entry in feed.entries[:10]:  # Latest 10 entries
                published_date = self._parse_entry_date(entry)
                incident = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "published": published_date.isoformat() if published_date else None,
                    "link": entry.get("link", ""),
                }
                incidents.append(incident)

                # Find the first incident that's not in the future
                if not latest_incident and published_date:
                    hours_ago = (datetime.utcnow() - published_date).total_seconds() / 3600
                    # Only use this incident if it's not in the future
                    if hours_ago >= 0:
                        latest_incident = {**incident, "published_datetime": published_date}  # Keep datetime for processing
                elif not latest_incident and not published_date:
                    # If no date, use it (assume it's current)
                    latest_incident = {**incident, "published_datetime": None}

            # Determine status from latest incident
            status = StatusType.OPERATIONAL
            has_recent_incident = False

            if latest_incident:
                title = latest_incident["title"].lower()
                summary_text = strip_html(latest_incident.get("summary", "")).lower()

                # Check if incident is resolved (check both title and summary)
                resolved_keywords = ["resolved", "completed", "fixed", "corrected", "restored", "mitigated", "resolved:"]
                is_resolved = any(word in title or word in summary_text for word in resolved_keywords)

                # Check if incident is informational/minor (doesn't affect core service)
                informational_keywords = [
                    "delayed", "backlog", "may be delayed", "summary", "summaries",
                    "no operational impact", "informational", "announcement",
                    "ip address changes", "scheduled", "update:"
                ]
                is_informational = any(word in title or word in summary_text for word in informational_keywords)

                # Check if incident is recent (within 24 hours) and NOT in the future
                if latest_incident.get("published_datetime"):
                    hours_ago = (datetime.utcnow() - latest_incident["published_datetime"]).total_seconds() / 3600
                    # Only consider it recent if it's in the past and within 24 hours
                    has_recent_incident = 0 <= hours_ago < 24

                # Determine status based on incident state
                if is_resolved or not has_recent_incident or is_informational:
                    # Old, future, resolved, or informational incidents don't affect status
                    status = StatusType.OPERATIONAL
                # Check for actual outages/incidents (not just monitoring)
                elif any(word in summary_text for word in ["outage", "down", "major outage", "critical", "unavailable"]):
                    status = StatusType.INCIDENT
                elif any(word in title for word in ["outage", "down", "major", "critical"]):
                    status = StatusType.INCIDENT
                # Check for degraded service (investigating/identified = active work)
                elif any(word in summary_text for word in ["investigating", "identified"]):
                    status = StatusType.DEGRADED
                # "Monitoring" alone (without outage) = operational (just watching)
                elif any(word in summary_text for word in ["monitoring"]) and not any(word in summary_text for word in ["outage", "down", "degraded"]):
                    status = StatusType.OPERATIONAL
                elif any(word in title for word in ["maintenance", "scheduled"]):
                    status = StatusType.MAINTENANCE
                else:
                    # Recent unresolved incident - mark as degraded
                    status = StatusType.DEGRADED

            raw_data = {
                "incidents": incidents,
                "feed_title": feed.feed.get("title", ""),
                "feed_updated": feed.feed.get("updated", ""),
                "has_recent_incident": has_recent_incident,
            }

            # Generate appropriate summary
            if status == StatusType.OPERATIONAL:
                # If operational, show "All systems operational" instead of old incident titles
                summary = "All systems operational"
            elif latest_incident:
                # Use the title from the latest non-future incident we determined
                summary = latest_incident.get("title", "Active incident")
            else:
                summary = "No recent incidents"

            last_changed = latest_incident.get("published_datetime") if latest_incident and has_recent_incident else None

            return {
                "status": status,
                "summary": summary,
                "raw_data": raw_data,
                "last_changed_at": last_changed,
            }

        except Exception as e:
            logger.error(f"Error parsing RSS feed from {url}: {e}")
            raise

    def _parse_entry_date(self, entry: dict) -> datetime:
        """Parse entry publication date."""
        # Try different date fields
        for field in ["published_parsed", "updated_parsed"]:
            if field in entry and entry[field]:
                try:
                    return datetime(*entry[field][:6])
                except:
                    pass

        # Try string parsing
        for field in ["published", "updated"]:
            if field in entry:
                try:
                    return datetime.fromisoformat(entry[field].replace("Z", "+00:00"))
                except:
                    pass

        return None
