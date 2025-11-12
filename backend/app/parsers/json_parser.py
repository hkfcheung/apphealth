"""JSON feed parser (e.g., Atlassian Statuspage API)."""
import json
from datetime import datetime
from typing import Dict, Any
from app.parsers.base import BaseParser
from app.models import StatusType
from app.utils.normalizer import normalize_status, normalize_component_statuses, extract_summary
import logging

logger = logging.getLogger(__name__)


class JSONParser(BaseParser):
    """Parser for JSON status feeds (Statuspage.io format)."""

    def can_parse(self, content_type: str, content: str) -> bool:
        """Check if content is JSON."""
        if "json" in content_type.lower():
            return True
        # Try to detect JSON by parsing
        try:
            json.loads(content)
            return True
        except:
            return False

    async def parse(self, content: str, url: str) -> Dict[str, Any]:
        """Parse JSON status feed."""
        try:
            data = json.loads(content)

            # Statuspage.io summary.json format
            if "status" in data:
                status_data = data.get("status", {})
                indicator = status_data.get("indicator", "").lower()
                description = status_data.get("description", "")

                # Map indicator to status
                status = self._map_indicator_to_status(indicator)

                # Get components if available
                components = data.get("components", [])
                if components:
                    component_status = normalize_component_statuses(components)
                    # Use worst status
                    if component_status.value != StatusType.OPERATIONAL.value:
                        status = component_status

                # Extract last changed time
                last_changed = None
                if "updated_at" in status_data:
                    last_changed = self._parse_timestamp(status_data["updated_at"])

                summary = extract_summary(data, "json")

                return {
                    "status": status,
                    "summary": summary,
                    "raw_data": data,
                    "last_changed_at": last_changed,
                }

            # Generic JSON format - try to infer structure
            else:
                status = StatusType.UNKNOWN
                summary = "Status information retrieved"

                # Look for common status fields
                for key in ["status", "state", "health", "overall_status"]:
                    if key in data:
                        status = normalize_status(str(data[key]))
                        break

                return {
                    "status": status,
                    "summary": summary,
                    "raw_data": data,
                    "last_changed_at": None,
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {url}: {e}")
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing JSON from {url}: {e}")
            raise

    def _map_indicator_to_status(self, indicator: str) -> StatusType:
        """Map Statuspage indicator to StatusType."""
        mapping = {
            "none": StatusType.OPERATIONAL,
            "minor": StatusType.DEGRADED,
            "major": StatusType.INCIDENT,
            "critical": StatusType.INCIDENT,
            "maintenance": StatusType.MAINTENANCE,
        }
        return mapping.get(indicator, StatusType.UNKNOWN)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            return None
