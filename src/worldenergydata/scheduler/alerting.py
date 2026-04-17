"""Email alerting for scheduler failures and staleness.

Per D-15: SMTP configured via .env (SMTP_HOST, SMTP_USER, SMTP_PASS).
Per D-16: Alert on (1) job failure after all retries, (2) staleness threshold breached.
Partial success (0 records) does NOT trigger alerts.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

logger = logging.getLogger(__name__)


class AlertSender:
    """Send email alerts via SMTP for scheduler events.

    Args:
        smtp_host: SMTP server hostname (None disables sending).
        smtp_user: SMTP authentication username.
        smtp_pass: SMTP authentication password.
        smtp_port: SMTP server port (default 587 for STARTTLS).
        recipients: List of email addresses to receive alerts.
                    Defaults to [smtp_user] if empty and smtp_user set.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        smtp_port: int = 587,
        recipients: Optional[List[str]] = None,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.smtp_port = smtp_port
        self.recipients = recipients or ([smtp_user] if smtp_user else [])
        self._enabled = bool(smtp_host and smtp_user and smtp_pass)

    @property
    def enabled(self) -> bool:
        """Whether SMTP alerting is configured and active."""
        return self._enabled

    def send_alert(self, subject: str, body: str) -> None:
        """Send an alert email.

        If SMTP is not configured, the alert is logged but not sent
        (graceful degradation for environments without SMTP).

        Args:
            subject: Email subject line.
            body: Plain-text email body.
        """
        if not self._enabled:
            logger.warning("SMTP not configured; alert logged only: %s", subject)
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            logger.info("Alert sent: %s", subject)
        except Exception as exc:
            logger.error("Failed to send alert '%s': %s", subject, exc)
