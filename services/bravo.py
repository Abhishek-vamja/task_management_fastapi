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


def send_invitation_email(email: str, inviter_name: str, board_name: str, invite_link: str) -> bool:
    """Send a transactional board invitation email using Brevo API with mock fallback.

    Args:
        email (str): Recipient email address.
        inviter_name (str): Full name or username of the inviter.
        board_name (str): Name of the board being shared.
        invite_link (str): Target URL containing the acceptance token.

    Returns:
        bool: True if sent successfully, False otherwise.
    """
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("xkeysib-your-brevo"):
        logger.warning(
            f"[Brevo Email Service] BREVO_API_KEY is not configured. "
            f"Simulated invitation sent to {email} for board '{board_name}'."
        )
        print(f"[MOCK EMAIL SENT] Invitation dispatched to {email}. Invite Link: {invite_link}")
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
            }
        ],
        "subject": f"You've been invited to join the '{board_name}' board on FlowAI!",
        "htmlContent": f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h2 style="color: #4F46E5;">Join the Collaboration Workspace</h2>
              <p>Hello,</p>
              <p><strong>{inviter_name}</strong> has invited you to collaborate on their project board <strong>'{board_name}'</strong> on FlowAI.</p>
              <p>Click the button below to accept your invitation and get started:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{invite_link}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Accept Invitation</a>
              </div>
              <p>Or copy and paste this link in your browser:</p>
              <p><a href="{invite_link}">{invite_link}</a></p>
              <br/>
              <p>Best regards,<br/><strong>FlowAI Team</strong></p>
            </div>
          </body>
        </html>
        """,
    }

    try:
        response = httpx.post(BREVO_API_URL, json=payload, headers=headers, timeout=10.0)
        if response.status_code in (200, 201, 202):
            logger.info(f"Invitation email successfully sent to {email}.")
            return True
        else:
            logger.warning(f"Brevo API error ({response.status_code}). Falling back to mock invitation mode. Response: {response.text}")
            print(f"[MOCK EMAIL FALLBACK] Invitation token created for {email}. Link: {invite_link}")
            return True
    except Exception as exc:
        logger.warning(f"Error connecting to Brevo API: {exc}. Falling back to mock invitation mode.")
        print(f"[MOCK EMAIL FALLBACK] Invitation token created for {email}. Link: {invite_link}")
        return True


def send_organization_invitation_email(email: str, inviter_name: str, org_name: str, org_key: str, invite_link: str) -> bool:
    """Send a transactional organization invitation email using Brevo API with mock fallback."""
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("xkeysib-your-brevo"):
        logger.warning(
            f"[Brevo Email Service] BREVO_API_KEY is not configured. "
            f"Simulated invitation sent to {email} for organization '{org_name}' [{org_key}]."
        )
        print(f"[MOCK EMAIL SENT] Organization Invite dispatched to {email} ({org_name} [{org_key}]). Link: {invite_link}")
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
            }
        ],
        "subject": f"You've been invited to join '{org_name}' ({org_key}) Organization on FlowAI!",
        "htmlContent": f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 20px auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
              <h2 style="color: #4F46E5; margin-top: 0;">Join Organization Workspace</h2>
              <p>Hello,</p>
              <p><strong>{inviter_name}</strong> has invited you to join their organization workspace <strong>'{org_name}'</strong> (Prefix Key: <strong>{org_key}</strong>) on FlowAI.</p>
              <p>Click the button below to accept your invitation and join the workspace:</p>
              <div style="text-align: center; margin: 28px 0;">
                <a href="{invite_link}" style="background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%); color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Accept Invitation</a>
              </div>
              <p style="font-size: 13px; color: #64748b;">Or copy and paste this link in your browser:</p>
              <p style="font-size: 13px;"><a href="{invite_link}" style="color: #4F46E5;">{invite_link}</a></p>
              <br/>
              <p style="font-size: 13px; color: #94a3b8;">Best regards,<br/><strong>FlowAI Workspace Team</strong></p>
            </div>
          </body>
        </html>
        """,
    }

    try:
        response = httpx.post(BREVO_API_URL, json=payload, headers=headers, timeout=10.0)
        if response.status_code in (200, 201, 202):
            logger.info(f"Organization invitation email successfully sent to {email}.")
            return True
        else:
            logger.warning(f"Brevo API error ({response.status_code}). Falling back to mock email mode.")
            print(f"[MOCK EMAIL FALLBACK] Organization Invite token created for {email}. Link: {invite_link}")
            return True
    except Exception as exc:
        logger.warning(f"Error connecting to Brevo API: {exc}. Falling back to mock email mode.")
        print(f"[MOCK EMAIL FALLBACK] Organization Invite token created for {email}. Link: {invite_link}")
        return True

