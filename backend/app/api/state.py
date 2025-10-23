"""State API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.database import get_session
from app.models import Site, Reading, SiteState, StatusType
from app.polling import polling_scheduler
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/state", tags=["state"])


@router.get("", response_model=List[SiteState])
async def get_all_states(session: Session = Depends(get_session)):
    """Get current state for all sites."""
    sites = session.exec(select(Site)).all()

    states = []
    for site in sites:
        state = await _get_site_state(site, session)
        states.append(state)

    return states


@router.get("/{site_id}", response_model=SiteState)
async def get_site_state(site_id: str, session: Session = Depends(get_session)):
    """Get current state for a specific site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    return await _get_site_state(site, session)


async def _get_site_state(site: Site, session: Session) -> SiteState:
    """Helper to build SiteState from site and latest reading."""
    # Get latest reading
    latest_reading = session.exec(
        select(Reading)
        .where(Reading.site_id == site.id)
        .order_by(Reading.created_at.desc())
        .limit(1)
    ).first()

    if latest_reading:
        status = latest_reading.status
        summary = latest_reading.summary
        last_checked_at = latest_reading.created_at
        last_changed_at = latest_reading.last_changed_at
        source_type = latest_reading.source_type
        error_message = latest_reading.error_message
    else:
        status = StatusType.UNKNOWN
        summary = "Not yet polled"
        last_checked_at = None
        last_changed_at = None
        source_type = None
        error_message = None

    # Get next poll time
    next_poll_at = polling_scheduler.get_next_poll_time(site.id)

    return SiteState(
        site_id=site.id,
        display_name=site.display_name,
        status_page=site.status_page,
        feed_url=site.feed_url,
        parser=site.parser,
        console_only=site.console_only,
        status=status,
        summary=summary,
        last_checked_at=last_checked_at,
        last_changed_at=last_changed_at,
        next_poll_at=next_poll_at,
        source_type=source_type,
        error_message=error_message,
        poll_frequency_seconds=site.poll_frequency_seconds,
        downdetector_url=site.downdetector_url,
        latest_downdetector_screenshot=site.latest_downdetector_screenshot,
        downdetector_screenshot_uploaded_at=site.downdetector_screenshot_uploaded_at,
    )


@router.post("/pause")
async def pause_polling():
    """Pause all polling."""
    polling_scheduler.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume_polling():
    """Resume polling."""
    polling_scheduler.resume()
    return {"status": "resumed"}


@router.post("/reload")
async def reload_sites():
    """Reload all sites and reschedule polling."""
    await polling_scheduler.reload_sites()
    return {"status": "reloaded"}
