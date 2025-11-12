"""Email notification service."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.models import Site, StatusType, AppSettings
from app.database import engine, Session

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles email notifications for status changes."""

    @staticmethod
    def get_settings() -> Optional[AppSettings]:
        """Get application settings from database."""
        with Session(engine) as session:
            return session.get(AppSettings, 1)

    @staticmethod
    def is_configured() -> bool:
        """Check if email is properly configured."""
        settings = EmailNotifier.get_settings()
        if not settings:
            return False

        return all([
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
            settings.notification_email,
        ])

    @staticmethod
    def should_notify(site: Site, new_status: StatusType, old_status: StatusType) -> bool:
        """
        Determine if we should send a notification.

        Rules:
        1. Only notify on transitions FROM operational TO non-operational
        2. Don't notify if we're still in the same non-operational state
        3. Respect cooldown period to prevent spam
        4. Notify when returning to operational after an incident
        """
        # Email not configured
        if not EmailNotifier.is_configured():
            return False

        # No status change
        if new_status == old_status:
            return False

        # Check cooldown period
        if site.last_notified_at:
            app_settings = EmailNotifier.get_settings()
            cooldown_minutes = app_settings.notification_cooldown_minutes if app_settings else 60

            cooldown_expires = site.last_notified_at + timedelta(minutes=cooldown_minutes)
            if datetime.utcnow() < cooldown_expires:
                logger.info(
                    f"Skipping notification for {site.display_name} - cooldown active until {cooldown_expires}"
                )
                return False

        # Notify on degradation from operational
        if old_status == StatusType.OPERATIONAL and new_status not in [StatusType.OPERATIONAL, StatusType.RECENTLY_RESOLVED]:
            return True

        # Notify when going from operational to recently resolved (brief issue occurred)
        if old_status == StatusType.OPERATIONAL and new_status == StatusType.RECENTLY_RESOLVED:
            return True

        # Notify on recovery to operational or recently resolved (after being degraded/incident)
        if old_status in [StatusType.DEGRADED, StatusType.INCIDENT, StatusType.MAINTENANCE] and new_status in [StatusType.OPERATIONAL, StatusType.RECENTLY_RESOLVED]:
            # Only if we previously notified about the degradation
            if site.last_notified_status and site.last_notified_status not in [StatusType.OPERATIONAL, StatusType.RECENTLY_RESOLVED]:
                return True

        return False

    @staticmethod
    def send_notification(
        site: Site,
        new_status: StatusType,
        old_status: StatusType,
        summary: Optional[str] = None
    ) -> bool:
        """
        Send email notification about status change.

        Returns True if notification was sent successfully.
        """
        if not EmailNotifier.is_configured():
            logger.warning("Email not configured - skipping notification")
            return False

        app_settings = EmailNotifier.get_settings()
        if not app_settings:
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = EmailNotifier._create_subject(site, new_status, old_status)
            msg['From'] = app_settings.smtp_from_email
            msg['To'] = app_settings.notification_email

            # Create email body
            text_body = EmailNotifier._create_text_body(site, new_status, old_status, summary)
            html_body = EmailNotifier._create_html_body(site, new_status, old_status, summary)

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(app_settings.smtp_host, app_settings.smtp_port) as server:
                server.starttls()
                server.login(app_settings.smtp_username, app_settings.smtp_password)
                server.send_message(msg)

            logger.info(
                f"Sent notification for {site.display_name}: {old_status} → {new_status}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send notification for {site.display_name}: {e}")
            return False

    @staticmethod
    def send_test_email(app_settings: AppSettings) -> bool:
        """Send a test email to verify SMTP configuration."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "✅ Status Dashboard - Test Email"
            msg['From'] = app_settings.smtp_from_email
            msg['To'] = app_settings.notification_email

            text_body = """
Status Dashboard Test Email
============================

This is a test email from your Status Dashboard.

If you received this email, your SMTP configuration is working correctly!

Time: {}
""".format(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))

            html_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .content { padding: 20px; background: #f9fafb; border-radius: 8px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>✅ Test Email Successful!</h2>
        </div>
        <div class="content">
            <p>This is a test email from your <strong>Status Dashboard</strong>.</p>
            <p>If you received this email, your SMTP configuration is working correctly!</p>
            <p><small>Sent: {}</small></p>
        </div>
    </div>
</body>
</html>
""".format(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(app_settings.smtp_host, app_settings.smtp_port) as server:
                server.starttls()
                server.login(app_settings.smtp_username, app_settings.smtp_password)
                server.send_message(msg)

            logger.info("Test email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False

    @staticmethod
    def _create_subject(site: Site, new_status: StatusType, old_status: StatusType) -> str:
        """Create email subject line."""
        if new_status == StatusType.OPERATIONAL:
            return f"✅ {site.display_name} - Service Restored"
        elif new_status == StatusType.RECENTLY_RESOLVED:
            return f"🔄 {site.display_name} - Recently Resolved"
        elif new_status == StatusType.DEGRADED:
            return f"⚠️ {site.display_name} - Performance Degraded"
        elif new_status == StatusType.INCIDENT:
            return f"🚨 {site.display_name} - Incident Detected"
        elif new_status == StatusType.MAINTENANCE:
            return f"🔧 {site.display_name} - Maintenance in Progress"
        else:
            return f"❓ {site.display_name} - Status Unknown"

    @staticmethod
    def _create_text_body(
        site: Site,
        new_status: StatusType,
        old_status: StatusType,
        summary: Optional[str]
    ) -> str:
        """Create plain text email body."""
        status_emoji = {
            StatusType.OPERATIONAL: "✅",
            StatusType.RECENTLY_RESOLVED: "🔄",
            StatusType.DEGRADED: "⚠️",
            StatusType.INCIDENT: "🚨",
            StatusType.MAINTENANCE: "🔧",
            StatusType.UNKNOWN: "❓",
        }

        body = f"""
Status Change Alert
{'=' * 50}

Service: {site.display_name}
Status: {status_emoji.get(old_status, '')} {old_status.upper()} → {status_emoji.get(new_status, '')} {new_status.upper()}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
        if summary:
            body += f"Summary: {summary}\n\n"

        body += f"""
Status Page: {site.status_page}

{'=' * 50}
This is an automated notification from your Status Dashboard.
"""
        return body

    @staticmethod
    def _create_html_body(
        site: Site,
        new_status: StatusType,
        old_status: StatusType,
        summary: Optional[str]
    ) -> str:
        """Create HTML email body."""
        status_colors = {
            StatusType.OPERATIONAL: "#10b981",  # green
            StatusType.RECENTLY_RESOLVED: "#84cc16",  # lime (yellow-green)
            StatusType.DEGRADED: "#f59e0b",     # orange
            StatusType.INCIDENT: "#ef4444",     # red
            StatusType.MAINTENANCE: "#3b82f6",  # blue
            StatusType.UNKNOWN: "#6b7280",      # gray
        }

        status_emoji = {
            StatusType.OPERATIONAL: "✅",
            StatusType.RECENTLY_RESOLVED: "🔄",
            StatusType.DEGRADED: "⚠️",
            StatusType.INCIDENT: "🚨",
            StatusType.MAINTENANCE: "🔧",
            StatusType.UNKNOWN: "❓",
        }

        old_color = status_colors.get(old_status, "#6b7280")
        new_color = status_colors.get(new_status, "#6b7280")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .status-change {{ display: flex; align-items: center; gap: 10px; margin: 20px 0; }}
        .status-badge {{
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            color: white;
        }}
        .arrow {{ font-size: 24px; color: #6b7280; }}
        .info {{ margin: 20px 0; }}
        .info-row {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #6b7280; }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin-top: 20px;
        }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">🔔 Status Change Alert</h2>
        </div>

        <div class="info">
            <div class="info-row">
                <span class="label">Service:</span> {site.display_name}
            </div>
            <div class="info-row">
                <span class="label">Time:</span> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>

        <div class="status-change">
            <span class="status-badge" style="background: {old_color};">
                {status_emoji.get(old_status, '')} {old_status.upper()}
            </span>
            <span class="arrow">→</span>
            <span class="status-badge" style="background: {new_color};">
                {status_emoji.get(new_status, '')} {new_status.upper()}
            </span>
        </div>

        {f'<div class="info-row"><span class="label">Summary:</span> {summary}</div>' if summary else ''}

        <a href="{site.status_page}" class="button">View Status Page</a>

        <div class="footer">
            This is an automated notification from your Status Dashboard.
        </div>
    </div>
</body>
</html>
"""
