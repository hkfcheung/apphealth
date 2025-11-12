"""Tests for status normalization utilities."""
import pytest
from app.models import StatusType
from app.utils.normalizer import (
    normalize_status,
    normalize_component_statuses,
    extract_summary,
)


class TestNormalizeStatus:
    """Test normalize_status function."""

    def test_operational_patterns(self):
        """Test operational status detection."""
        assert normalize_status("All Systems Operational") == StatusType.OPERATIONAL
        assert normalize_status("operational") == StatusType.OPERATIONAL
        assert normalize_status("OK") == StatusType.OPERATIONAL
        assert normalize_status("Normal") == StatusType.OPERATIONAL
        assert normalize_status("No issues") == StatusType.OPERATIONAL

    def test_degraded_patterns(self):
        """Test degraded status detection."""
        assert normalize_status("Degraded Performance") == StatusType.DEGRADED
        assert normalize_status("Investigating Issue") == StatusType.DEGRADED
        assert normalize_status("Minor Issues") == StatusType.DEGRADED
        assert normalize_status("Partial Outage") == StatusType.DEGRADED

    def test_incident_patterns(self):
        """Test incident status detection."""
        assert normalize_status("Major Outage") == StatusType.INCIDENT
        assert normalize_status("Service Down") == StatusType.INCIDENT
        assert normalize_status("Critical Incident") == StatusType.INCIDENT

    def test_maintenance_patterns(self):
        """Test maintenance status detection."""
        assert normalize_status("Scheduled Maintenance") == StatusType.MAINTENANCE
        assert normalize_status("Planned Work") == StatusType.MAINTENANCE

    def test_unknown_patterns(self):
        """Test unknown status detection."""
        assert normalize_status("") == StatusType.UNKNOWN
        assert normalize_status("Random Text") == StatusType.UNKNOWN
        assert normalize_status(None) == StatusType.UNKNOWN

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalize_status("OPERATIONAL") == StatusType.OPERATIONAL
        assert normalize_status("Operational") == StatusType.OPERATIONAL
        assert normalize_status("operational") == StatusType.OPERATIONAL


class TestNormalizeComponentStatuses:
    """Test normalize_component_statuses function."""

    def test_all_operational(self):
        """Test all operational components."""
        components = [
            {"status": "operational"},
            {"status": "operational"},
        ]
        assert normalize_component_statuses(components) == StatusType.OPERATIONAL

    def test_worst_status_wins(self):
        """Test that worst status is returned."""
        components = [
            {"status": "operational"},
            {"status": "degraded"},
            {"status": "operational"},
        ]
        assert normalize_component_statuses(components) == StatusType.DEGRADED

    def test_incident_priority(self):
        """Test that incident has highest priority."""
        components = [
            {"status": "operational"},
            {"status": "degraded"},
            {"status": "major outage"},
        ]
        assert normalize_component_statuses(components) == StatusType.INCIDENT

    def test_empty_components(self):
        """Test empty component list."""
        assert normalize_component_statuses([]) == StatusType.UNKNOWN


class TestExtractSummary:
    """Test extract_summary function."""

    def test_rss_with_incidents(self):
        """Test RSS summary extraction with incidents."""
        data = {
            "incidents": [
                {"title": "Service Degradation Identified"},
                {"title": "Database Performance Issues"},
            ]
        }
        summary = extract_summary(data, "rss")
        assert summary == "Service Degradation Identified"

    def test_rss_no_incidents(self):
        """Test RSS summary with no incidents."""
        data = {"incidents": []}
        summary = extract_summary(data, "rss")
        assert summary == "All systems operational"

    def test_json_with_status_description(self):
        """Test JSON summary extraction."""
        data = {
            "status": {
                "description": "All Systems Operational"
            }
        }
        summary = extract_summary(data, "json")
        assert summary == "All Systems Operational"

    def test_json_with_incidents(self):
        """Test JSON summary with incidents."""
        data = {
            "incidents": [
                {"name": "Database Connectivity Issues"}
            ]
        }
        summary = extract_summary(data, "json")
        assert summary == "Database Connectivity Issues"

    def test_html_summary(self):
        """Test HTML summary extraction."""
        data = {"summary": "Custom status message"}
        summary = extract_summary(data, "html")
        assert summary == "Custom status message"
