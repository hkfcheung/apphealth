"""Sites API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import os
import uuid

from app.database import get_session
from app.models import Site, Reading, ParserType
from app.polling import polling_scheduler
import logging

logger = logging.getLogger(__name__)

# Directory for uploaded screenshots
SCREENSHOTS_DIR = "/data/downdetector_screenshots"

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=List[Site])
async def list_sites(session: Session = Depends(get_session)):
    """List all sites."""
    sites = session.exec(select(Site)).all()
    return sites


@router.get("/{site_id}", response_model=Site)
async def get_site(site_id: str, session: Session = Depends(get_session)):
    """Get a specific site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.post("", response_model=Site)
async def create_site(site: Site, session: Session = Depends(get_session)):
    """Create a new site."""
    # Check if site already exists
    existing = session.get(Site, site.id)
    if existing:
        raise HTTPException(status_code=400, detail="Site ID already exists")

    site.created_at = datetime.utcnow()
    site.updated_at = datetime.utcnow()

    session.add(site)
    session.commit()
    session.refresh(site)

    # Add to polling schedule
    if site.is_active and not site.console_only:
        await polling_scheduler.add_site_to_schedule(site.id)

    logger.info(f"Created site: {site.id}")
    return site


@router.put("/{site_id}", response_model=Site)
async def update_site(
    site_id: str,
    site_update: Site,
    session: Session = Depends(get_session)
):
    """Update a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Update fields
    update_data = site_update.model_dump(exclude_unset=True, exclude={"id", "created_at"})
    for key, value in update_data.items():
        setattr(site, key, value)

    site.updated_at = datetime.utcnow()

    session.add(site)
    session.commit()
    session.refresh(site)

    # Update schedule
    if site.is_active and not site.console_only:
        await polling_scheduler.add_site_to_schedule(site.id)
    else:
        polling_scheduler.remove_site_from_schedule(site.id)

    logger.info(f"Updated site: {site.id}")
    return site


@router.delete("/{site_id}")
async def delete_site(site_id: str, session: Session = Depends(get_session)):
    """Delete a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Remove from schedule
    polling_scheduler.remove_site_from_schedule(site.id)

    # Delete readings
    readings = session.exec(select(Reading).where(Reading.site_id == site_id)).all()
    for reading in readings:
        session.delete(reading)

    session.delete(site)
    session.commit()

    logger.info(f"Deleted site: {site.id}")
    return {"status": "deleted", "site_id": site_id}


@router.post("/{site_id}/poll")
async def poll_site_now(site_id: str, session: Session = Depends(get_session)):
    """Trigger an immediate poll for a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if site.console_only:
        raise HTTPException(status_code=400, detail="Cannot poll console-only sites")

    await polling_scheduler.poll_site_now(site_id)

    return {"status": "polling", "site_id": site_id}


@router.get("/{site_id}/history")
async def get_site_history(
    site_id: str,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """Get historical readings for a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    readings = session.exec(
        select(Reading)
        .where(Reading.site_id == site_id)
        .order_by(Reading.created_at.desc())
        .limit(limit)
    ).all()

    return readings


@router.post("/{site_id}/downdetector-screenshot")
async def upload_downdetector_screenshot(
    site_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Upload a DownDetector screenshot for a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.downdetector_url:
        raise HTTPException(status_code=400, detail="Site does not have a DownDetector URL configured")

    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Ensure directory exists
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
    filename = f"{site_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_extension}"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)

    # Save file
    try:
        contents = await file.read()
        with open(filepath, 'wb') as f:
            f.write(contents)

        # Update site with latest screenshot
        site.latest_downdetector_screenshot = filename
        site.downdetector_screenshot_uploaded_at = datetime.utcnow()
        session.add(site)
        session.commit()
        session.refresh(site)

        logger.info(f"Uploaded DownDetector screenshot for {site_id}: {filename}")

        return {
            "status": "uploaded",
            "filename": filename,
            "uploaded_at": site.downdetector_screenshot_uploaded_at
        }

    except Exception as e:
        logger.error(f"Error saving screenshot: {e}")
        raise HTTPException(status_code=500, detail="Failed to save screenshot")


@router.get("/{site_id}/downdetector-screenshot")
async def get_downdetector_screenshot(site_id: str, session: Session = Depends(get_session)):
    """Get the latest DownDetector screenshot for a site."""
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.latest_downdetector_screenshot:
        raise HTTPException(status_code=404, detail="No screenshot available")

    filepath = os.path.join(SCREENSHOTS_DIR, site.latest_downdetector_screenshot)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Screenshot file not found")

    return FileResponse(
        filepath,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"}
    )
