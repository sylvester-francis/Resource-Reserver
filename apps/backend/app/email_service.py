"""Email notification service using FastAPI-Mail.

This module provides an asynchronous email service for sending various types
of notifications within the Resource Reserver application. It leverages
FastAPI-Mail for SMTP communication and Jinja2 for HTML template rendering.

Features:
    - Asynchronous email sending with async/await support
    - Jinja2 HTML template rendering with automatic escaping
    - Fallback to plain text when templates are unavailable
    - Lazy initialization for efficient resource usage
    - Comprehensive logging for debugging and monitoring
    - Support for single or multiple recipients

Supported Email Types:
    - Reservation confirmations
    - Reservation reminders
    - Waitlist position updates
    - Resource availability alerts

Example:
    Basic usage with the global service instance::

        from app.email_service import email_service

        # Send a simple email
        await email_service.send_email(
            to="user@example.com",
            subject="Test Email",
            body="This is a test message."
        )

        # Send a reservation confirmation
        await email_service.send_reservation_confirmation(
            to="user@example.com",
            username="John Doe",
            resource_name="Conference Room A",
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 11, 0),
            reservation_id=123
        )

Note:
    The email service must be enabled via configuration settings. When disabled,
    all send operations will return False without attempting to send.

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
    """Service for sending email notifications.

    This class provides a unified interface for sending various types of email
    notifications. It supports both plain text and HTML template-based emails,
    with lazy initialization to defer resource allocation until first use.

    The service integrates with FastAPI-Mail for SMTP communication and uses
    Jinja2 templates for rendering HTML emails. If templates are unavailable,
    it falls back to plain text content.

    Attributes:
        _settings: Application settings containing SMTP configuration.
        _mail: FastMail client instance for sending emails. None until initialized.
        _templates: Jinja2 Environment for template rendering. None until initialized.
        _initialized: Flag indicating whether the service has been initialized.

    Example:
        Creating and using the email service::

            service = EmailService()

            # Check if service is enabled
            if service.enabled:
                await service.send_email(
                    to="user@example.com",
                    subject="Welcome",
                    body="Welcome to Resource Reserver!"
                )
    """

    def __init__(self) -> None:
        """Initialize the EmailService instance.

        Creates a new EmailService with default uninitialized state. The actual
        SMTP connection and template loading are deferred until first use via
        lazy initialization in the _initialize method.
        """
        self._settings = get_settings()
        self._mail: FastMail | None = None
        self._templates: Environment | None = None
        self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if email service is enabled.

        Returns:
            bool: True if email service is enabled in settings, False otherwise.
        """
        return self._settings.email_enabled

    def _get_connection_config(self) -> ConnectionConfig:
        """Get FastAPI-Mail connection configuration.

        Builds a ConnectionConfig object from application settings for use
        with the FastMail client.

        Returns:
            ConnectionConfig: Configuration object containing SMTP server details,
                credentials, and TLS/SSL settings.
        """
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
        """Initialize mail client and template engine.

        Performs lazy initialization of the FastMail client and Jinja2 template
        environment. This method is idempotent and will only initialize once.

        The initialization process includes:
            1. Creating the FastMail client with SMTP configuration
            2. Loading Jinja2 templates from the configured directory
            3. Setting up HTML/XML autoescaping for security

        If the email service is disabled or initialization fails, the service
        will remain in an uninitialized state and send operations will be skipped.

        Note:
            This method catches all exceptions during initialization to prevent
            email failures from crashing the application. Errors are logged
            for debugging purposes.
        """
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

        Loads and renders a Jinja2 template file with the provided context
        variables. Templates are expected to be HTML files located in the
        configured templates directory.

        Args:
            template_name: Name of the template file (e.g., "confirmation.html").
            context: Dictionary of variables to pass to the template for rendering.

        Returns:
            str | None: Rendered HTML string if successful, None if the template
                environment is not initialized or rendering fails.

        Note:
            Template rendering errors are logged but not raised, allowing the
            caller to fall back to plain text content.
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
        """Send an email to one or more recipients.

        This is the core email sending method that handles both plain text and
        HTML template-based emails. If a template is specified and renders
        successfully, it will be used; otherwise, the plain text body is sent.

        Args:
            to: Recipient email address as a string, or list of email addresses
                for multiple recipients.
            subject: Email subject line.
            body: Plain text body content. Used as fallback if template rendering
                fails or no template is specified.
            template_name: Optional name of the HTML template file to render.
                Should include the file extension (e.g., "welcome.html").
            template_context: Optional dictionary of variables to pass to the
                template for rendering. Required if template_name is provided.

        Returns:
            bool: True if the email was sent successfully, False if the service
                is disabled, not initialized, or sending failed.

        Example:
            Sending a plain text email::

                await service.send_email(
                    to="user@example.com",
                    subject="Hello",
                    body="This is a plain text message."
                )

            Sending an HTML template email::

                await service.send_email(
                    to=["user1@example.com", "user2@example.com"],
                    subject="Newsletter",
                    body="Fallback text content",
                    template_name="newsletter.html",
                    template_context={"title": "Monthly Update"}
                )
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
        """Send a reservation confirmation email.

        Notifies the user that their reservation has been successfully created.
        Includes details about the reserved resource, time slot, and a unique
        reservation ID for reference.

        Args:
            to: Recipient email address.
            username: Display name of the user who made the reservation.
            resource_name: Name of the reserved resource (e.g., "Conference Room A").
            start_time: Reservation start date and time.
            end_time: Reservation end date and time.
            reservation_id: Unique identifier for the reservation.

        Returns:
            bool: True if the confirmation email was sent successfully,
                False otherwise.

        Example:
            Sending a confirmation for a meeting room reservation::

                await service.send_reservation_confirmation(
                    to="john.doe@example.com",
                    username="John Doe",
                    resource_name="Board Room",
                    start_time=datetime(2024, 3, 15, 14, 0),
                    end_time=datetime(2024, 3, 15, 16, 0),
                    reservation_id=456
                )
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
        """Send a reservation reminder email.

        Sends a reminder notification before a reservation starts, helping users
        prepare for their upcoming resource usage.

        Args:
            to: Recipient email address.
            username: Display name of the user with the reservation.
            resource_name: Name of the reserved resource.
            start_time: Reservation start date and time.
            hours_until: Number of hours until the reservation starts. Used in
                the subject line and email body.
            reservation_id: Unique identifier for the reservation.

        Returns:
            bool: True if the reminder email was sent successfully,
                False otherwise.

        Example:
            Sending a 24-hour reminder::

                await service.send_reservation_reminder(
                    to="jane.doe@example.com",
                    username="Jane Doe",
                    resource_name="Lab Equipment A",
                    start_time=datetime(2024, 3, 16, 9, 0),
                    hours_until=24,
                    reservation_id=789
                )
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
        """Send a waitlist position update email.

        Notifies users when their position in a resource waitlist changes or
        when a slot becomes available for them to claim.

        Args:
            to: Recipient email address.
            username: Display name of the user on the waitlist.
            resource_name: Name of the resource being waited for.
            position: Current position in the waitlist (1-indexed).
            action: Type of waitlist update. Supported values:
                - "position_changed": User's position in the queue has changed.
                - "slot_available": A slot has opened and the user can claim it.
                Defaults to "position_changed".

        Returns:
            bool: True if the update email was sent successfully,
                False otherwise.

        Example:
            Notifying a user that a slot is available::

                await service.send_waitlist_update(
                    to="user@example.com",
                    username="Alex Smith",
                    resource_name="3D Printer",
                    position=1,
                    action="slot_available"
                )
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
        """Send a resource availability notification email.

        Alerts users when a resource they are interested in becomes available
        for reservation during a specific time window.

        Args:
            to: Recipient email address.
            username: Display name of the user to notify.
            resource_name: Name of the resource that has become available.
            available_from: Start of the availability window.
            available_until: End of the availability window.

        Returns:
            bool: True if the notification email was sent successfully,
                False otherwise.

        Example:
            Notifying a user about resource availability::

                await service.send_resource_available(
                    to="user@example.com",
                    username="Chris Johnson",
                    resource_name="Video Conference Room",
                    available_from=datetime(2024, 3, 20, 13, 0),
                    available_until=datetime(2024, 3, 20, 17, 0)
                )
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
