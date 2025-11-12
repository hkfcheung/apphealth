"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "sqlite:///./status_dashboard.db"

    # Polling
    default_poll_frequency: int = 300  # 5 minutes
    max_concurrent_scrapes: int = 5
    request_timeout: int = 60  # Increased for heavy pages like M365 admin

    # Retry & backoff
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # Scraping
    user_agent: str = "StatusDashboard/1.0 (+https://github.com/yourusername/status-dashboard)"
    respect_robots_txt: bool = True

    # API
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Email notifications
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    notification_email: Optional[str] = None
    notification_cooldown_minutes: int = 60  # Don't spam - wait 60 min between notifications per site

    class Config:
        env_file = ".env"


settings = Settings()
