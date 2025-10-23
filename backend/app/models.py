"""Database models."""
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ParserType(str, Enum):
    """Parser types."""
    AUTO = "auto"
    RSS = "rss"
    JSON = "json"
    HTML = "html"


class StatusType(str, Enum):
    """Service status types."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    INCIDENT = "incident"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class Site(SQLModel, table=True):
    """Monitored site configuration."""

    __tablename__ = "sites"

    id: str = Field(primary_key=True)
    display_name: str = Field(index=True)
    status_page: str
    feed_url: Optional[str] = None
    poll_frequency_seconds: int = Field(default=300)
    parser: ParserType = Field(default=ParserType.AUTO)
    is_active: bool = Field(default=True)
    console_only: bool = Field(default=False)  # For AWS Health Dashboard etc.
    use_playwright: bool = Field(default=False)  # Use headless browser for dynamic content
    auth_state_file: Optional[str] = None  # Path to saved authentication state for Playwright
    downdetector_url: Optional[str] = None  # DownDetector URL for user-reported issues
    latest_downdetector_screenshot: Optional[str] = None  # Filename of latest uploaded screenshot
    downdetector_screenshot_uploaded_at: Optional[datetime] = None  # When screenshot was uploaded
    last_notified_at: Optional[datetime] = None  # Last time we sent a notification for this site
    last_notified_status: Optional[StatusType] = None  # Status we last notified about
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    readings: List["Reading"] = Relationship(back_populates="site")


class Reading(SQLModel, table=True):
    """Status reading/snapshot."""

    __tablename__ = "readings"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(foreign_key="sites.id", index=True)
    status: StatusType
    summary: Optional[str] = None
    source_type: str  # "rss", "json", "html"
    raw_snapshot: dict = Field(default={}, sa_column=Column(JSON))
    last_changed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    downdetector_reports: Optional[int] = None  # User reports from DownDetector (deprecated)
    downdetector_chart: Optional[str] = None  # Filename of DownDetector chart screenshot
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    site: Site = Relationship(back_populates="readings")


class AppSettings(SQLModel, table=True):
    """Application settings stored in database."""

    __tablename__ = "app_settings"

    id: int = Field(default=1, primary_key=True)  # Single row for settings

    # SMTP settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    notification_email: Optional[str] = None
    notification_cooldown_minutes: int = 60

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SiteState(SQLModel):
    """Current state view for a site (not a table)."""

    site_id: str
    display_name: str
    status_page: str
    feed_url: Optional[str]
    parser: ParserType
    console_only: bool
    status: StatusType
    summary: Optional[str]
    last_checked_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    next_poll_at: Optional[datetime]
    source_type: Optional[str]
    error_message: Optional[str]
    poll_frequency_seconds: int
    downdetector_url: Optional[str]
    latest_downdetector_screenshot: Optional[str] = None
    downdetector_screenshot_uploaded_at: Optional[datetime] = None
