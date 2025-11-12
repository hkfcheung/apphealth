"""Advisory analysis service."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select

from app.models import Advisory, SiteModule, Site, CriticalityLevel
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class AdvisoryService:
    """Service for extracting and analyzing service advisories."""

    @staticmethod
    async def extract_advisories_from_feed(feed_data: dict) -> List[Dict[str, Any]]:
        """
        Extract advisories from parsed feed data.

        Args:
            feed_data: Parsed feed data from RSS/Atom parser

        Returns:
            List of advisory dictionaries with fields:
                - title: str
                - description: str
                - severity: str (optional)
                - published_at: datetime (optional)
                - source_url: str (optional)
        """
        advisories = []

        # Extract from 'incidents' field if present
        incidents = feed_data.get('raw_data', {}).get('incidents', [])

        for incident in incidents:
            advisory = {
                'title': incident.get('title', ''),
                'description': incident.get('description', ''),
                'severity': incident.get('severity'),
                'published_at': incident.get('published_at'),
                'source_url': incident.get('link'),
            }

            # Only add if we have at least a title
            if advisory['title']:
                advisories.append(advisory)

        # If no incidents found, try to extract from summary
        if not advisories and feed_data.get('summary'):
            # Create a single advisory from the current status
            advisories.append({
                'title': feed_data.get('summary', 'Status Update'),
                'description': feed_data.get('summary', ''),
                'severity': None,
                'published_at': feed_data.get('last_changed_at'),
                'source_url': None,
            })

        return advisories

    @staticmethod
    async def analyze_and_store_advisory(
        session: Session,
        site_id: str,
        advisory_data: Dict[str, Any]
    ) -> Optional[Advisory]:
        """
        Analyze an advisory and store it in the database.

        Args:
            session: Database session
            site_id: Site ID
            advisory_data: Advisory data dict (from extract_advisories_from_feed)

        Returns:
            The created Advisory object, or None if skipped
        """
        # Get site
        site = session.get(Site, site_id)
        if not site:
            logger.warning(f"Site {site_id} not found")
            return None

        # Check if advisory already exists (based on title and site)
        existing = session.exec(
            select(Advisory)
            .where(Advisory.site_id == site_id)
            .where(Advisory.title == advisory_data['title'])
        ).first()

        if existing:
            logger.debug(f"Advisory already exists: {advisory_data['title']}")
            return existing

        # Get configured modules for this site
        modules = session.exec(
            select(SiteModule)
            .where(SiteModule.site_id == site_id)
            .where(SiteModule.enabled == True)
        ).all()

        module_names = [m.module_name for m in modules]

        # Analyze with LLM
        analysis = await LLMService.analyze_advisory(
            title=advisory_data['title'],
            description=advisory_data['description'] or advisory_data['title'],
            severity=advisory_data.get('severity'),
            configured_modules=module_names,
            service_name=site.display_name
        )

        # Map criticality string to enum
        criticality_map = {
            'high': CriticalityLevel.HIGH,
            'medium': CriticalityLevel.MEDIUM,
            'low': CriticalityLevel.LOW,
        }
        criticality = criticality_map.get(
            analysis['criticality'].lower(),
            CriticalityLevel.UNKNOWN
        )

        # Create advisory
        advisory = Advisory(
            site_id=site_id,
            title=advisory_data['title'],
            description=advisory_data['description'],
            severity=advisory_data.get('severity'),
            criticality=criticality,
            affects_us=analysis['affects_us'],
            affected_modules=analysis['affected_modules'],
            relevance_reason=analysis['relevance_reason'],
            source_url=advisory_data.get('source_url'),
            published_at=advisory_data.get('published_at'),
        )

        session.add(advisory)
        session.commit()
        session.refresh(advisory)

        logger.info(
            f"Stored advisory for {site_id}: {advisory.title} "
            f"(criticality={advisory.criticality}, affects_us={advisory.affects_us})"
        )

        return advisory

    @staticmethod
    async def process_site_advisories(
        session: Session,
        site_id: str,
        feed_data: dict
    ) -> List[Advisory]:
        """
        Extract and analyze all advisories for a site.

        Args:
            session: Database session
            site_id: Site ID
            feed_data: Parsed feed data

        Returns:
            List of created/updated Advisory objects
        """
        # Extract advisories from feed
        advisory_data_list = await AdvisoryService.extract_advisories_from_feed(feed_data)

        if not advisory_data_list:
            logger.debug(f"No advisories extracted for {site_id}")
            return []

        logger.info(f"Extracted {len(advisory_data_list)} advisories for {site_id}")

        # Analyze and store each advisory
        created_advisories = []
        for advisory_data in advisory_data_list:
            try:
                advisory = await AdvisoryService.analyze_and_store_advisory(
                    session=session,
                    site_id=site_id,
                    advisory_data=advisory_data
                )
                if advisory:
                    created_advisories.append(advisory)
            except Exception as e:
                logger.error(f"Failed to analyze advisory '{advisory_data.get('title')}': {e}")
                continue

        return created_advisories

    @staticmethod
    async def cleanup_old_advisories(session: Session, days: int = 30):
        """
        Clean up advisories older than specified days.

        Args:
            session: Database session
            days: Number of days to keep
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        old_advisories = session.exec(
            select(Advisory)
            .where(Advisory.created_at < cutoff)
        ).all()

        for advisory in old_advisories:
            session.delete(advisory)

        session.commit()

        if old_advisories:
            logger.info(f"Cleaned up {len(old_advisories)} old advisories")
