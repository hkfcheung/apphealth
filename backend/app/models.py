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
    RECENTLY_RESOLVED = "recently_resolved"
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


class SiteModule(SQLModel, table=True):
    """Modules/packages that a user cares about for a site."""

    __tablename__ = "site_modules"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(foreign_key="sites.id", index=True)
    module_name: str  # e.g., "Exchange Online", "Teams", "SharePoint Online"
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CriticalityLevel(str, Enum):
    """Advisory criticality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Advisory(SQLModel, table=True):
    """Service advisories and notices."""

    __tablename__ = "advisories"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(foreign_key="sites.id", index=True)

    # Advisory details
    title: str
    description: Optional[str] = None
    severity: Optional[str] = None  # Vendor's severity level
    criticality: CriticalityLevel = Field(default=CriticalityLevel.UNKNOWN)  # Our analysis

    # Relevance
    affects_us: bool = Field(default=False)  # Does it affect our configured modules?
    affected_modules: List[str] = Field(default=[], sa_column=Column(JSON))  # Which modules
    relevance_reason: Optional[str] = None  # LLM explanation of why it's relevant

    # Metadata
    is_informational: bool = Field(default=False)
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ChatMessage(SQLModel, table=True):
    """Admin chat messages for querying status data."""

    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    role: str  # "user" or "assistant"
    content: str
    context_data: Optional[dict] = Field(default={}, sa_column=Column(JSON))  # Relevant data for this message
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


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

    # LLM settings
    llm_provider: Optional[str] = None  # "openai", "anthropic", "ollama", "huggingface"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None  # Model name depends on provider

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
