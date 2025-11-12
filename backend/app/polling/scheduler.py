"""Polling scheduler for monitoring sites."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
import logging

from app.models import Site, Reading, StatusType
from app.database import engine
from app.parsers import parser_factory
from app.config import settings
from app.notifications import EmailNotifier
from app.services.advisory_service import AdvisoryService

logger = logging.getLogger(__name__)


class PollingScheduler:
    """Manages scheduled polling of status sites."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.next_poll_times: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            logger.info("Starting polling scheduler...")
            self.scheduler.start()
            self.is_running = True
            # Schedule initial load of sites
            asyncio.create_task(self.reload_sites())
            logger.info("Polling scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            logger.info("Stopping polling scheduler...")
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Polling scheduler stopped")

    def pause(self):
        """Pause all polling."""
        logger.info("Pausing polling...")
        self.scheduler.pause()

    def resume(self):
        """Resume polling."""
        logger.info("Resuming polling...")
        self.scheduler.resume()

    async def reload_sites(self):
        """Reload all active sites and schedule their polls."""
        async with self._lock:
            logger.info("Reloading sites...")
            with Session(engine) as session:
                sites = session.exec(
                    select(Site).where(Site.is_active == True)
                ).all()

                # Remove existing jobs
                self.scheduler.remove_all_jobs()
                self.next_poll_times.clear()

                # Schedule each site
                for site in sites:
                    if site.console_only:
                        logger.info(f"Skipping console-only site: {site.id}")
                        continue

                    job_id = f"poll_{site.id}"

                    # Add job with interval trigger
                    self.scheduler.add_job(
                        self.poll_site,
                        trigger=IntervalTrigger(seconds=site.poll_frequency_seconds),
                        id=job_id,
                        args=[site.id],
                        replace_existing=True,
                        max_instances=1,
                    )

                    # Set initial next poll time
                    self.next_poll_times[site.id] = datetime.utcnow() + timedelta(
                        seconds=site.poll_frequency_seconds
                    )

                    logger.info(
                        f"Scheduled polling for {site.id} every {site.poll_frequency_seconds}s"
                    )

                # Trigger immediate poll for all sites
                for site in sites:
                    if not site.console_only:
                        asyncio.create_task(self.poll_site(site.id))

    async def poll_site(self, site_id: str):
        """Poll a single site and store the reading."""
        logger.info(f"Polling site: {site_id}")

        try:
            with Session(engine) as session:
                site = session.get(Site, site_id)
                if not site or not site.is_active:
                    logger.warning(f"Site {site_id} not found or inactive")
                    return

                # Determine URL to fetch
                url = site.feed_url if site.feed_url else site.status_page

                # Parse the URL
                result = await parser_factory.parse_url(
                    url,
                    site.parser,
                    use_playwright=site.use_playwright,
                    auth_state_file=site.auth_state_file
                )

                # Filter by configured modules if any exist
                from app.models import SiteModule
                modules = session.exec(
                    select(SiteModule)
                    .where(SiteModule.site_id == site_id)
                    .where(SiteModule.enabled == True)
                ).all()

                if modules and result.get("raw_data", {}).get("components"):
                    # Get list of configured module names
                    module_names = [m.module_name.lower() for m in modules]
                    all_components = result["raw_data"]["components"]

                    # Filter to only configured components
                    filtered_components = [
                        comp for comp in all_components
                        if comp["name"].lower() in module_names
                    ]

                    if filtered_components:
                        # Re-determine status based on filtered components
                        from app.models import StatusType
                        worst_status = StatusType.OPERATIONAL

                        for comp in filtered_components:
                            comp_status_str = comp.get("status", "operational")
                            # Find worst status among filtered components
                            if comp_status_str == "incident":
                                worst_status = StatusType.INCIDENT
                            elif comp_status_str == "degraded" and worst_status != StatusType.INCIDENT:
                                worst_status = StatusType.DEGRADED
                            elif comp_status_str == "maintenance" and worst_status == StatusType.OPERATIONAL:
                                worst_status = StatusType.MAINTENANCE

                        # Update result with filtered status
                        result["status"] = worst_status
                        affected_names = [c["name"] for c in filtered_components if c["status"] != "operational"]
                        if affected_names:
                            result["summary"] = f"{', '.join(affected_names)}: {worst_status.value}"
                        else:
                            result["summary"] = f"Monitored components operational ({len(filtered_components)} components)"

                        logger.info(f"Filtered to {len(filtered_components)} configured modules for {site_id}")

                # Get previous reading to detect changes
                last_reading = session.exec(
                    select(Reading)
                    .where(Reading.site_id == site_id)
                    .order_by(Reading.created_at.desc())
                    .limit(1)
                ).first()

                # Determine last_changed_at
                last_changed_at = result.get("last_changed_at")
                if not last_changed_at:
                    # If status changed from last reading, set to now
                    if last_reading and last_reading.status != result["status"]:
                        last_changed_at = datetime.utcnow()
                    elif last_reading:
                        last_changed_at = last_reading.last_changed_at

                # Create reading
                reading = Reading(
                    site_id=site_id,
                    status=result["status"],
                    summary=result["summary"],
                    source_type=result["source_type"],
                    raw_snapshot=result.get("raw_data", {}),
                    last_changed_at=last_changed_at,
                    error_message=result.get("error"),
                    created_at=datetime.utcnow(),
                )

                session.add(reading)
                session.commit()

                # Process advisories (extract and analyze)
                try:
                    advisories = await AdvisoryService.process_site_advisories(
                        session=session,
                        site_id=site_id,
                        feed_data=result
                    )
                    if advisories:
                        logger.info(f"Processed {len(advisories)} advisories for {site_id}")
                except Exception as advisory_error:
                    logger.error(f"Failed to process advisories for {site_id}: {advisory_error}")

                # Check if we should send a notification
                old_status = last_reading.status if last_reading else StatusType.UNKNOWN
                new_status = result["status"]

                if EmailNotifier.should_notify(site, new_status, old_status):
                    success = EmailNotifier.send_notification(
                        site, new_status, old_status, result["summary"]
                    )
                    if success:
                        # Update notification tracking
                        site.last_notified_at = datetime.utcnow()
                        site.last_notified_status = new_status
                        session.add(site)
                        session.commit()

                logger.info(
                    f"Poll complete for {site_id}: {result['status']} via {result['source_type']}"
                )

                # Update next poll time
                self.next_poll_times[site_id] = datetime.utcnow() + timedelta(
                    seconds=site.poll_frequency_seconds
                )

        except Exception as e:
            logger.error(f"Error polling site {site_id}: {e}")
            # Store error reading
            try:
                with Session(engine) as session:
                    reading = Reading(
                        site_id=site_id,
                        status=StatusType.UNKNOWN,
                        summary="Polling failed",
                        source_type="error",
                        error_message=str(e),
                        created_at=datetime.utcnow(),
                    )
                    session.add(reading)
                    session.commit()
            except Exception as db_error:
                logger.error(f"Failed to save error reading: {db_error}")

    async def poll_site_now(self, site_id: str):
        """Trigger an immediate poll for a site."""
        logger.info(f"Manual poll triggered for {site_id}")
        await self.poll_site(site_id)

    def get_next_poll_time(self, site_id: str) -> Optional[datetime]:
        """Get the next scheduled poll time for a site."""
        return self.next_poll_times.get(site_id)

    async def add_site_to_schedule(self, site_id: str):
        """Add a single site to the schedule."""
        with Session(engine) as session:
            site = session.get(Site, site_id)
            if not site or not site.is_active or site.console_only:
                return

            job_id = f"poll_{site.id}"

            self.scheduler.add_job(
                self.poll_site,
                trigger=IntervalTrigger(seconds=site.poll_frequency_seconds),
                id=job_id,
                args=[site.id],
                replace_existing=True,
                max_instances=1,
            )

            self.next_poll_times[site.id] = datetime.utcnow() + timedelta(
                seconds=site.poll_frequency_seconds
            )

            logger.info(f"Added {site.id} to schedule")

            # Trigger immediate poll
            asyncio.create_task(self.poll_site(site.id))

    def remove_site_from_schedule(self, site_id: str):
        """Remove a site from the schedule."""
        job_id = f"poll_{site_id}"
        try:
            self.scheduler.remove_job(job_id)
            self.next_poll_times.pop(site_id, None)
            logger.info(f"Removed {site_id} from schedule")
        except:
            pass


# Global scheduler instance
polling_scheduler = PollingScheduler()
