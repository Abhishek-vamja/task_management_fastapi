"""Brevo (Bravo) Email Service module for sending transactional emails."""

import logging
import httpx
from apps.config import BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_welcome_email(email: str, username: str) -> bool:
    """Send a transactional welcome email to a newly registered user using Brevo API.

    Args:
        email (str): Recipient email address.
        username (str): Registered user's username.

    Returns:
        bool: True if email request was sent successfully, False otherwise.
    """
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("xkeysib-your-brevo"):
        logger.warning(
            f"[Brevo Email Service] BREVO_API_KEY is not configured or using default template value. "
            f"Simulated welcome email sent to {email} ({username})."
        )
        print(f"[MOCK EMAIL SENT] Welcome email dispatched to {email} for user '{username}'")
        return True

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL,
        },
        "to": [
            {
                "email": email,
                "name": username,
            }
        ],
        "subject": "Welcome to Task Management API!",
        "htmlContent": f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h2 style="color: #4F46E5;">Welcome to Task Management API, {username}!</h2>
              <p>Thank you for registering your account. We are excited to have you on board!</p>
              <p>You can now log in and start managing your tasks efficiently.</p>
              <br/>
              <p>Best regards,<br/><strong>Task Management Team</strong></p>
            </div>
          </body>
        </html>
        """,
    }

    try:
        response = httpx.post(BREVO_API_URL, json=payload, headers=headers, timeout=10.0)
        if response.status_code in (200, 201, 202):
            logger.info(f"Welcome email successfully sent to {email} via Brevo API.")
            return True
        else:
            logger.error(
                f"Failed to send welcome email to {email}. Status code: {response.status_code}, "
                f"Response: {response.text}"
            )
            return False
    except Exception as exc:
        logger.error(f"Error connecting to Brevo API while sending welcome email to {email}: {exc}")
        return False
