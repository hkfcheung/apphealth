"""Admin API endpoints for application settings."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from app.database import get_session
from app.models import AppSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class SettingsUpdate(BaseModel):
    """Settings update request."""
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    notification_email: Optional[str] = None
    notification_cooldown_minutes: int = 60


@router.get("/settings", response_model=AppSettings)
async def get_settings(session: Session = Depends(get_session)):
    """Get application settings."""
    settings = session.get(AppSettings, 1)
    if not settings:
        # Create default settings if they don't exist
        settings = AppSettings(id=1)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    return settings


@router.put("/settings", response_model=AppSettings)
async def update_settings(
    settings_update: SettingsUpdate,
    session: Session = Depends(get_session)
):
    """Update application settings."""
    settings = session.get(AppSettings, 1)
    if not settings:
        settings = AppSettings(id=1)
        session.add(settings)

    # Update fields
    settings.smtp_host = settings_update.smtp_host
    settings.smtp_port = settings_update.smtp_port
    settings.smtp_username = settings_update.smtp_username

    # Only update password if provided (don't clear it)
    if settings_update.smtp_password:
        settings.smtp_password = settings_update.smtp_password

    settings.smtp_from_email = settings_update.smtp_from_email
    settings.notification_email = settings_update.notification_email
    settings.notification_cooldown_minutes = settings_update.notification_cooldown_minutes
    settings.updated_at = datetime.utcnow()

    session.add(settings)
    session.commit()
    session.refresh(settings)

    logger.info("Application settings updated")
    return settings


@router.post("/settings/test-email")
async def test_email(session: Session = Depends(get_session)):
    """Send a test email to verify SMTP configuration."""
    from app.notifications import EmailNotifier

    settings = session.get(AppSettings, 1)
    if not settings:
        raise HTTPException(status_code=400, detail="Settings not configured")

    # Check if email is configured
    if not all([
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.smtp_from_email,
        settings.notification_email,
    ]):
        raise HTTPException(
            status_code=400,
            detail="Email not fully configured. Please fill in all SMTP fields."
        )

    try:
        success = EmailNotifier.send_test_email(settings)
        if success:
            return {"status": "success", "message": "Test email sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
