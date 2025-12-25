"""Email notification service using FastAPI-Mail.

Provides async email sending with Jinja2 templates for:
- Reservation confirmations
- Reservation reminders
- Waitlist updates
- Resource availability alerts

Author: Sylvester-Francis
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._mail: FastMail | None = None
        self._templates: Environment | None = None
        self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if email service is enabled."""
        return self._settings.email_enabled

    def _get_connection_config(self) -> ConnectionConfig:
        """Get FastAPI-Mail connection configuration."""
        return ConnectionConfig(
            MAIL_USERNAME=self._settings.smtp_user,
            MAIL_PASSWORD=self._settings.smtp_password,
            MAIL_FROM=self._settings.smtp_from,
            MAIL_FROM_NAME=self._settings.smtp_from_name,
            MAIL_PORT=self._settings.smtp_port,
            MAIL_SERVER=self._settings.smtp_host,
            MAIL_STARTTLS=self._settings.smtp_tls,
            MAIL_SSL_TLS=self._settings.smtp_ssl,
            USE_CREDENTIALS=bool(self._settings.smtp_user),
            VALIDATE_CERTS=True,
        )

    def _initialize(self) -> None:
        """Initialize mail client and template engine."""
        if self._initialized:
            return

        if not self.enabled:
            logger.info("Email service is disabled")
            return

        try:
            config = self._get_connection_config()
            self._mail = FastMail(config)

            # Setup Jinja2 templates
            templates_path = Path(self._settings.email_templates_dir)
            if templates_path.exists():
                self._templates = Environment(
                    loader=FileSystemLoader(str(templates_path)),
                    autoescape=select_autoescape(["html", "xml"]),
                )
                logger.info(f"Email templates loaded from {templates_path}")
            else:
                logger.warning(f"Email templates directory not found: {templates_path}")

            self._initialized = True
            logger.info("Email service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize email service: {e}")
            self._initialized = False

    def _render_template(
        self, template_name: str, context: dict[str, Any]
    ) -> str | None:
        """Render an email template with the given context.

        Args:
            template_name: Name of the template file.
            context: Template variables.

        Returns:
            Rendered HTML string or None if template not found.
        """
        if not self._templates:
            return None

        try:
            template = self._templates.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return None

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        template_name: str | None = None,
        template_context: dict[str, Any] | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: Recipient email address(es).
            subject: Email subject.
            body: Plain text body (fallback if template fails).
            template_name: Optional HTML template name.
            template_context: Optional template variables.

        Returns:
            True if email sent successfully, False otherwise.
        """
        self._initialize()

        if not self.enabled or not self._mail:
            logger.debug("Email service disabled, skipping send")
            return False

        try:
            recipients = [to] if isinstance(to, str) else to

            # Try to render HTML template
            html_body = None
            if template_name and template_context:
                html_body = self._render_template(template_name, template_context)

            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=html_body or body,
                subtype=MessageType.html if html_body else MessageType.plain,
            )

            await self._mail.send_message(message)
            logger.info(f"Email sent successfully to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_reservation_confirmation(
        self,
        to: str,
        username: str,
        resource_name: str,
        start_time: datetime,
        end_time: datetime,
        reservation_id: int,
    ) -> bool:
        """Send reservation confirmation email.

        Args:
            to: Recipient email.
            username: User's name.
            resource_name: Name of the reserved resource.
            start_time: Reservation start time.
            end_time: Reservation end time.
            reservation_id: Reservation ID.

        Returns:
            True if email sent successfully.
        """
        subject = f"Reservation Confirmed: {resource_name}"

        context = {
            "username": username,
            "resource_name": resource_name,
            "start_time": start_time.strftime("%B %d, %Y at %I:%M %p"),
            "end_time": end_time.strftime("%B %d, %Y at %I:%M %p"),
            "reservation_id": reservation_id,
            "year": datetime.now().year,
        }

        body = f"""
Hello {username},

Your reservation has been confirmed!

Resource: {resource_name}
Start: {context["start_time"]}
End: {context["end_time"]}
Reservation ID: #{reservation_id}

Thank you for using Resource Reserver.
        """

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            template_name="reservation_confirmation.html",
            template_context=context,
        )

    async def send_reservation_reminder(
        self,
        to: str,
        username: str,
        resource_name: str,
        start_time: datetime,
        hours_until: int,
        reservation_id: int,
    ) -> bool:
        """Send reservation reminder email.

        Args:
            to: Recipient email.
            username: User's name.
            resource_name: Name of the reserved resource.
            start_time: Reservation start time.
            hours_until: Hours until reservation starts.
            reservation_id: Reservation ID.

        Returns:
            True if email sent successfully.
        """
        subject = f"Reminder: {resource_name} reservation in {hours_until} hour(s)"

        context = {
            "username": username,
            "resource_name": resource_name,
            "start_time": start_time.strftime("%B %d, %Y at %I:%M %p"),
            "hours_until": hours_until,
            "reservation_id": reservation_id,
            "year": datetime.now().year,
        }

        body = f"""
Hello {username},

This is a reminder that your reservation is starting soon!

Resource: {resource_name}
Starts in: {hours_until} hour(s)
Start Time: {context["start_time"]}
Reservation ID: #{reservation_id}

Thank you for using Resource Reserver.
        """

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            template_name="reservation_reminder.html",
            template_context=context,
        )

    async def send_waitlist_update(
        self,
        to: str,
        username: str,
        resource_name: str,
        position: int,
        action: str = "position_changed",
    ) -> bool:
        """Send waitlist position update email.

        Args:
            to: Recipient email.
            username: User's name.
            resource_name: Name of the resource.
            position: Current position in waitlist.
            action: Type of update (position_changed, slot_available).

        Returns:
            True if email sent successfully.
        """
        if action == "slot_available":
            subject = f"Slot Available: {resource_name}"
            message = "A slot has become available for a resource you're waiting for!"
        else:
            subject = f"Waitlist Update: {resource_name}"
            message = "Your position in the waitlist has been updated."

        context = {
            "username": username,
            "resource_name": resource_name,
            "position": position,
            "action": action,
            "message": message,
            "year": datetime.now().year,
        }

        body = f"""
Hello {username},

{message}

Resource: {resource_name}
Your Position: #{position}

Visit the dashboard to check availability or accept a slot offer.

Thank you for using Resource Reserver.
        """

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            template_name="waitlist_update.html",
            template_context=context,
        )

    async def send_resource_available(
        self,
        to: str,
        username: str,
        resource_name: str,
        available_from: datetime,
        available_until: datetime,
    ) -> bool:
        """Send resource availability notification.

        Args:
            to: Recipient email.
            username: User's name.
            resource_name: Name of the resource.
            available_from: Start of availability window.
            available_until: End of availability window.

        Returns:
            True if email sent successfully.
        """
        subject = f"Resource Available: {resource_name}"

        context = {
            "username": username,
            "resource_name": resource_name,
            "available_from": available_from.strftime("%B %d, %Y at %I:%M %p"),
            "available_until": available_until.strftime("%B %d, %Y at %I:%M %p"),
            "year": datetime.now().year,
        }

        body = f"""
Hello {username},

Good news! A resource you were interested in is now available.

Resource: {resource_name}
Available From: {context["available_from"]}
Available Until: {context["available_until"]}

Visit the dashboard to make a reservation.

Thank you for using Resource Reserver.
        """

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            template_name="resource_available.html",
            template_context=context,
        )


# Global email service instance
email_service = EmailService()
