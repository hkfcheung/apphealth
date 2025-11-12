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

            # Extract incidents from entries and categorize them
            incidents = []
            active_incidents = []  # Unresolved incidents
            recent_resolved_incidents = []  # Resolved in last 24h
            latest_incident = None

            for entry in feed.entries[:20]:  # Check more entries to capture all recent incidents
                published_date = self._parse_entry_date(entry)

                # Skip future incidents
                if published_date:
                    hours_ago = (datetime.utcnow() - published_date).total_seconds() / 3600
                    if hours_ago < 0:  # Future incident
                        continue

                incident = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "published": published_date.isoformat() if published_date else None,
                    "link": entry.get("link", ""),
                }
                # Keep datetime separately for processing (not in raw_data)
                incident_datetime = published_date
                incidents.append(incident)

                # Check if this incident is from the last 24 hours
                is_recent = False
                if incident_datetime:
                    hours_ago = (datetime.utcnow() - incident_datetime).total_seconds() / 3600
                    is_recent = 0 <= hours_ago < 24

                # Categorize incident as active or recently resolved
                title_lower = incident["title"].lower()
                summary_lower = strip_html(incident.get("summary", "")).lower()

                resolved_keywords = ["resolved", "completed", "fixed", "corrected", "restored", "mitigated"]
                is_resolved = any(word in title_lower or word in summary_lower for word in resolved_keywords)

                # Skip informational items
                informational_keywords = ["scheduled", "update:", "announcement", "no operational impact"]
                is_informational = any(word in title_lower or word in summary_lower for word in informational_keywords)

                if is_informational:
                    continue

                if is_recent:
                    if is_resolved:
                        recent_resolved_incidents.append({"incident": incident, "datetime": incident_datetime})
                    else:
                        active_incidents.append({"incident": incident, "datetime": incident_datetime})

                # Track the most recent non-future incident for status determination
                if not latest_incident:
                    latest_incident = {"incident": incident, "datetime": incident_datetime}

            # Determine status from incidents
            status = StatusType.OPERATIONAL
            has_recent_incident = len(active_incidents) > 0 or len(recent_resolved_incidents) > 0

            if active_incidents:
                # There are active unresolved incidents
                latest_incident = active_incidents[0]
                inc = latest_incident["incident"]
                title = inc["title"].lower()
                summary_text = strip_html(inc.get("summary", "")).lower()

                # Check for actual outages/incidents (not just monitoring)
                if any(word in summary_text for word in ["outage", "down", "major outage", "critical", "unavailable"]):
                    status = StatusType.INCIDENT
                elif any(word in title for word in ["outage", "down", "major", "critical"]):
                    status = StatusType.INCIDENT
                # Check for degraded service (investigating/identified/monitoring = incident still open)
                elif any(word in summary_text for word in ["investigating", "identified", "monitoring"]):
                    status = StatusType.DEGRADED
                elif any(word in title for word in ["maintenance", "scheduled"]):
                    status = StatusType.MAINTENANCE
                else:
                    # Recent unresolved incident - mark as degraded
                    status = StatusType.DEGRADED
            elif recent_resolved_incidents:
                # No active incidents, but there were incidents in the last 24h that are now resolved
                # Mark as RECENTLY_RESOLVED to show there was instability, but it's currently operational
                status = StatusType.RECENTLY_RESOLVED
                latest_incident = recent_resolved_incidents[0]
            else:
                # No active or recent incidents
                status = StatusType.OPERATIONAL

            raw_data = {
                "incidents": incidents,
                "active_incidents": [{"title": i["incident"]["title"], "link": i["incident"]["link"]} for i in active_incidents],
                "recent_resolved": [{"title": i["incident"]["title"], "link": i["incident"]["link"], "published": i["incident"]["published"]} for i in recent_resolved_incidents],
                "feed_title": feed.feed.get("title", ""),
                "feed_updated": feed.feed.get("updated", ""),
                "has_recent_incident": has_recent_incident,
            }

            # Generate appropriate summary
            if status == StatusType.OPERATIONAL:
                summary = "All systems operational"
            elif active_incidents:
                # Show active incident
                summary = latest_incident["incident"].get("title", "Active incident")
            elif recent_resolved_incidents:
                # Show recently resolved incidents (within last 24h) so they appear in the log
                if len(recent_resolved_incidents) == 1:
                    summary = f"Resolved: {recent_resolved_incidents[0]['incident']['title']}"
                else:
                    # Multiple resolved incidents
                    titles = [i["incident"]["title"] for i in recent_resolved_incidents[:3]]
                    summary = f"Resolved incidents: {', '.join(titles[:2])}"
                    if len(recent_resolved_incidents) > 2:
                        summary += f" (+{len(recent_resolved_incidents) - 2} more)"
            elif latest_incident:
                summary = latest_incident["incident"].get("title", "No recent incidents")
            else:
                summary = "No recent incidents"

            last_changed = latest_incident.get("datetime") if latest_incident and has_recent_incident else None

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
