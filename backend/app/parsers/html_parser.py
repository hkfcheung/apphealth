"""HTML scraper for status pages without feeds."""
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from app.parsers.base import BaseParser
from app.models import StatusType
from app.utils.normalizer import normalize_status
import logging
import re

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    """Parser for HTML status pages using BeautifulSoup."""

    def can_parse(self, content_type: str, content: str) -> bool:
        """Check if content is HTML."""
        if "html" in content_type.lower():
            return True
        if content.strip().startswith("<!DOCTYPE") or content.strip().startswith("<html"):
            return True
        return False

    async def parse(self, content: str, url: str) -> Dict[str, Any]:
        """Parse HTML status page."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Initialize components storage
            self._components = []

            # Try Microsoft 365 Admin Center first (for authenticated pages)
            if 'admin.microsoft.com' in url or 'admin.cloud.microsoft' in url:
                status, summary = self._extract_status_microsoft365(soup)
            else:
                status = StatusType.UNKNOWN
                summary = ""

            # Try StatusCast (Veeva) if not M365
            if status == StatusType.UNKNOWN:
                status, summary = self._extract_status_veeva(soup)

            # Then try Statuspage.io
            if status == StatusType.UNKNOWN:
                status, summary = self._extract_status_statuspage_io(soup)

            # Finally try generic extraction
            if status == StatusType.UNKNOWN:
                status, summary = self._extract_status_generic(soup)

            raw_data = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "summary": summary,
                "components": self._components if hasattr(self, '_components') else []
            }

            return {
                "status": status,
                "summary": summary,
                "raw_data": raw_data,
                "last_changed_at": None,  # Hard to determine from HTML
            }

        except Exception as e:
            logger.error(f"Error parsing HTML from {url}: {e}")
            raise

    def _extract_status_statuspage_io(self, soup: BeautifulSoup) -> tuple[StatusType, str]:
        """Extract status from Statuspage.io-based pages."""
        # Extract component-level status first
        components = []
        component_containers = soup.find_all('div', {'class': 'component-inner-container'})

        for container in component_containers:
            status_attr = container.get('data-component-status', '')
            name_elem = container.find('span', {'class': 'name'})

            if name_elem:
                component_name = name_elem.get_text(strip=True)
                # Map Statuspage.io statuses to our StatusType
                if status_attr == 'operational':
                    comp_status = StatusType.OPERATIONAL
                elif status_attr == 'degraded_performance':
                    comp_status = StatusType.DEGRADED
                elif status_attr == 'partial_outage':
                    comp_status = StatusType.DEGRADED
                elif status_attr == 'major_outage':
                    comp_status = StatusType.INCIDENT
                elif status_attr == 'under_maintenance':
                    comp_status = StatusType.MAINTENANCE
                else:
                    comp_status = StatusType.UNKNOWN

                components.append({
                    'name': component_name,
                    'status': comp_status.value
                })

        # Store components for later filtering
        # This will be stored in raw_data and can be filtered by module config
        self._components = components

        # Look for status indicator
        status_indicator = soup.find(class_=re.compile(r"status.*indicator", re.I))
        if status_indicator:
            classes = " ".join(status_indicator.get("class", []))
            if "none" in classes or "operational" in classes:
                return StatusType.OPERATIONAL, "All Systems Operational"
            elif "minor" in classes:
                return StatusType.DEGRADED, "Minor Service Issues"
            elif "major" in classes or "critical" in classes:
                return StatusType.INCIDENT, "Service Disruption"

        # Look for overall status text
        status_text_elem = soup.find(class_=re.compile(r"page-status", re.I))
        if status_text_elem:
            text = status_text_elem.get_text(strip=True)
            status = normalize_status(text)
            return status, text

        # Look for unresolved incidents
        incidents = soup.find_all(class_=re.compile(r"incident", re.I))
        unresolved_incidents = []
        for incident in incidents:
            if not re.search(r"resolved|completed", incident.get_text(), re.I):
                title_elem = incident.find(class_=re.compile(r"title|name", re.I))
                if title_elem:
                    unresolved_incidents.append(title_elem.get_text(strip=True))

        if unresolved_incidents:
            return StatusType.DEGRADED, unresolved_incidents[0]

        return StatusType.UNKNOWN, ""

    def _extract_status_generic(self, soup: BeautifulSoup) -> tuple[StatusType, str]:
        """Generic status extraction strategy."""
        # Look for common status keywords in prominent text
        header_texts = []

        # Check h1, h2 headers
        for header in soup.find_all(["h1", "h2", "h3"]):
            text = header.get_text(strip=True)
            if text:
                header_texts.append(text)

        # Check divs with status-related classes
        for div in soup.find_all("div", class_=re.compile(r"status|banner|alert|notice", re.I)):
            text = div.get_text(strip=True)
            if text and len(text) < 500:  # Avoid large content blocks
                header_texts.append(text)

        # Normalize and check
        for text in header_texts:
            status = normalize_status(text)
            if status != StatusType.UNKNOWN:
                return status, text[:200]  # Limit summary length

        # Fallback: look for "operational" or "incident" anywhere
        page_text = soup.get_text().lower()
        if re.search(r"all systems operational|everything is operational", page_text):
            return StatusType.OPERATIONAL, "All Systems Operational"
        if re.search(r"experiencing issues|service disruption|outage", page_text):
            return StatusType.DEGRADED, "Service Issues Detected"

        return StatusType.UNKNOWN, "Unable to determine status"

    def _extract_status_veeva(self, soup: BeautifulSoup) -> tuple[StatusType, str]:
        """Extract status from Veeva trust site (StatusCast-based)."""
        # First check individual components - these are the actual live status
        # Look for: <span class="status-list-component-status-text ... component-available">Normal</span>
        status_spans = soup.find_all("span", class_=re.compile(r"status-list-component-status-text"))

        if status_spans:
            # Count component statuses
            normal_count = 0
            maintenance_count = 0
            degraded_count = 0
            unavailable_count = 0

            for span in status_spans:
                text = span.get_text(strip=True).lower()
                classes = " ".join(span.get("class", []))

                if "component-available" in classes and text in ["normal", "operational", "available"]:
                    normal_count += 1
                elif "maintenance" in text or "maintenance" in classes:
                    maintenance_count += 1
                elif "degraded" in classes or "degraded" in text:
                    degraded_count += 1
                elif "unavailable" in classes or "unavailable" in text:
                    unavailable_count += 1

            total_components = normal_count + maintenance_count + degraded_count + unavailable_count

            # Report based on component statuses (most important)
            if unavailable_count > 0:
                return StatusType.INCIDENT, f"{unavailable_count} service(s) unavailable"
            elif degraded_count > 0:
                return StatusType.DEGRADED, f"{degraded_count} service(s) degraded"
            elif maintenance_count > 0 and normal_count == 0:
                # All components in maintenance
                return StatusType.MAINTENANCE, "System maintenance in progress"
            elif normal_count > 0:
                # Most/all components are normal - system is operational
                if maintenance_count > 0:
                    return StatusType.OPERATIONAL, f"All systems operational ({maintenance_count} scheduled maintenance)"
                return StatusType.OPERATIONAL, "All systems operational"

        # Fallback: Check overall status banner
        # Look for: <span class="current-status-comp-status-text">Maintenance</span>
        overall_status_span = soup.find("span", class_=re.compile(r"current-status-comp-status-text"))

        if overall_status_span:
            text = overall_status_span.get_text(strip=True).lower()

            if text in ["operational", "all systems operational", "normal"]:
                return StatusType.OPERATIONAL, "All systems operational"
            elif "incident" in text or "major" in text or "outage" in text:
                return StatusType.INCIDENT, "Service incident"
            elif "degraded" in text or "minor" in text:
                return StatusType.DEGRADED, "Service degraded"
            # Note: We don't trust "maintenance" banner - it's often stale or refers to scheduled events

        return StatusType.UNKNOWN, ""

    def _extract_status_microsoft365(self, soup: BeautifulSoup) -> tuple[StatusType, str]:
        """Extract status from Microsoft 365 Admin Center service health page."""
        page_text = soup.get_text()

        # Check if we're authenticated
        if 'sign in' in page_text.lower() and 'service health' not in page_text.lower():
            return StatusType.UNKNOWN, "Authentication required"

        # Look for service health status in the page
        # M365 admin center shows:
        # - "Incident" = Major outage (INCIDENT status)
        # - "Degraded" = Performance issues (DEGRADED status)
        # - "Advisory" = Informational only (OPERATIONAL status)
        # - "Healthy" = Normal operation (OPERATIONAL status)

        # Count actual incidents (not advisories)
        incident_count = 0

        # Look for active incidents (major issues)
        if re.search(r'(\d+)\s+active\s+incident', page_text, re.I):
            match = re.search(r'(\d+)\s+active\s+incident', page_text, re.I)
            incident_count = int(match.group(1))

        # Check for explicit service degradation status
        if re.search(r'(service degradation|degraded)', page_text, re.I):
            # Try to extract which service is degraded
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'(service degradation|degraded)', line, re.I):
                    # Look at nearby lines for service name
                    context = ' '.join(lines[max(0,i-2):min(len(lines),i+3)])
                    # Common M365 services
                    for service in ['Exchange Online', 'SharePoint', 'Teams', 'OneDrive', 'Outlook']:
                        if service.lower() in context.lower():
                            return StatusType.DEGRADED, f"{service}: Service degraded"
                    return StatusType.DEGRADED, "Service degradation detected"

        # Check for major outages/incidents
        if incident_count > 0:
            return StatusType.INCIDENT, f"{incident_count} active incident(s)"

        # Look for "Incident" status type (not Advisory)
        if re.search(r'\bIncident\b', page_text):
            # Found actual incident status
            return StatusType.INCIDENT, "Active service incident"

        # If we see "Healthy" status for services, that's operational
        # Count healthy services vs total services mentioned
        healthy_count = len(re.findall(r'Healthy', page_text))

        # If we found the service health page and see healthy services, it's operational
        if 'service health' in page_text.lower() and healthy_count > 5:
            # Check for advisories to mention them without changing status
            advisory_matches = re.findall(r'(\d+)\s+advisor(?:y|ies)', page_text, re.I)
            if advisory_matches:
                total_advisories = sum(int(m) for m in advisory_matches)
                return StatusType.OPERATIONAL, f"All services healthy ({total_advisories} informational advisories)"
            return StatusType.OPERATIONAL, "All services healthy"

        return StatusType.UNKNOWN, "Unable to determine status"
