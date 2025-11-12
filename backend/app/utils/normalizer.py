"""Status normalization utilities."""
from app.models import StatusType
import re


# Mapping patterns for status normalization
STATUS_PATTERNS = {
    StatusType.OPERATIONAL: [
        r"operational",
        r"all systems operational",
        r"no issues",
        r"normal",
        r"ok",
        r"up",
        r"available",
        r"healthy",
        r"none",
    ],
    StatusType.DEGRADED: [
        r"degraded",
        r"partial",
        r"minor",
        r"investigating",
        r"identified",
        r"monitoring",
        r"performance issues",
    ],
    StatusType.INCIDENT: [
        r"major outage",
        r"down",
        r"outage",
        r"incident",
        r"critical",
        r"service disruption",
        r"major",
    ],
    StatusType.MAINTENANCE: [
        r"maintenance",
        r"scheduled",
        r"planned work",
    ],
}


def normalize_status(status_text: str) -> StatusType:
    """
    Normalize a status string to a standard StatusType.

    Args:
        status_text: Raw status text from feed/scrape

    Returns:
        StatusType enum value
    """
    if not status_text:
        return StatusType.UNKNOWN

    text_lower = status_text.lower().strip()

    # Check patterns in priority order
    for status_type, patterns in STATUS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return status_type

    return StatusType.UNKNOWN


def normalize_component_statuses(components: list[dict]) -> StatusType:
    """
    Determine overall status from component list.

    Args:
        components: List of component dicts with 'status' key

    Returns:
        Overall StatusType (worst status wins)
    """
    if not components:
        return StatusType.UNKNOWN

    statuses = []
    for comp in components:
        status_text = comp.get("status", "")
        statuses.append(normalize_status(status_text))

    # Priority: incident > degraded > maintenance > operational > unknown
    if StatusType.INCIDENT in statuses:
        return StatusType.INCIDENT
    if StatusType.DEGRADED in statuses:
        return StatusType.DEGRADED
    if StatusType.MAINTENANCE in statuses:
        return StatusType.MAINTENANCE
    if StatusType.OPERATIONAL in statuses:
        return StatusType.OPERATIONAL

    return StatusType.UNKNOWN


def extract_summary(data: dict, source_type: str) -> str:
    """
    Extract a meaningful summary from parsed data.

    Args:
        data: Parsed data dict
        source_type: "rss", "json", or "html"

    Returns:
        Summary string
    """
    if source_type == "rss":
        # Get latest incident title
        incidents = data.get("incidents", [])
        if incidents:
            return incidents[0].get("title", "No summary available")
        return "All systems operational"

    elif source_type == "json":
        # Check for description or status message
        if "status" in data:
            desc = data["status"].get("description", "")
            if desc:
                return desc
        # Check for active incidents
        incidents = data.get("incidents", [])
        if incidents:
            return incidents[0].get("name", "Active incident")
        return "All systems operational"

    elif source_type == "html":
        return data.get("summary", "Status information retrieved from page")

    return "No summary available"
