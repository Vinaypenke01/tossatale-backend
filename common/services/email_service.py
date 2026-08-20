"""
common/services/email_service.py — Resend Email Dispatch Service
Handles transactional and editorial email deliveries via Resend API.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger("common.email_service")

RESEND_API_URL = "https://api.resend.com/emails"


def get_resend_api_key() -> str:
    return getattr(settings, "RESEND_API_KEY", "") or ""


def get_default_from_email() -> str:
    sender = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@tossatale.com") or "hello@tossatale.com"
    if "<" not in sender and "@" in sender:
        return f"Tossatale <{sender}>"
    return sender


class EmailService:
    """
    Centralized email delivery service using the Resend API.
    """

    @staticmethod
    def send_resend_email(
        to: str | list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
    ) -> dict:
        """
        Deliver an email using Resend REST API.
        """
        api_key = get_resend_api_key()
        if not api_key:
            logger.warning("RESEND_API_KEY is not set. Email delivery skipped.")
            return {"success": False, "message": "RESEND_API_KEY is not configured."}

        recipients = [to] if isinstance(to, str) else to
        sender = from_email or get_default_from_email()

        payload = {
            "from": sender,
            "to": recipients,
            "subject": subject,
            "html": html_content,
        }
        if text_content:
            payload["text"] = text_content

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code in [200, 201]:
                res_data = response.json()
                logger.info("Resend email sent successfully to %s (id: %s)", recipients, res_data.get("id"))
                return {"success": True, "id": res_data.get("id")}
            else:
                logger.error(
                    "Resend email failed with status %s: %s",
                    response.status_code,
                    response.text,
                )
                return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as exc:
            logger.exception("Exception occurred while sending email via Resend: %s", exc)
            return {"success": False, "error": str(exc)}

    # ──────────────────────────────────────────────────────────────────────────
    # Specific Email Notification Templates
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def send_password_reset_otp_email(
        to_email: str,
        otp_code: str,
        user_name: str = "Storyteller",
    ) -> dict:
        """
        Send a verification OTP code for password reset.
        """
        subject = f"Your Tossatale Verification Code: {otp_code}"

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tossatale Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c0d0e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0c0d0e; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" max-width="540px" cellspacing="0" cellpadding="0" border="0" style="max-width: 540px; background-color: #18181b; border: 1px solid #27272a; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
          
          <!-- Header -->
          <tr>
            <td style="padding: 36px 40px 20px 40px; text-align: center; border-bottom: 1px solid #27272a;">
              <h1 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">
                tossatale
              </h1>
              <p style="margin: 6px 0 0 0; font-size: 13px; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
                Security Verification
              </p>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding: 36px 40px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #e4e4e7; line-height: 1.6;">
                Hello {user_name},
              </p>
              <p style="margin: 0 0 28px 0; font-size: 15px; color: #a1a1aa; line-height: 1.6;">
                We received a request to reset the password for your Tossatale account. Enter the 6-digit verification code below to proceed:
              </p>

              <!-- OTP Code Display Card -->
              <div style="background-color: #09090b; border: 1px solid #3f3f46; border-radius: 14px; padding: 24px 16px; text-align: center; margin-bottom: 28px;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: 800; letter-spacing: 10px; color: #f97316; display: inline-block;">
                  {otp_code}
                </span>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #71717a; font-weight: 500;">
                  ⏱ Valid for 10 minutes · Single use only
                </p>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 14px; color: #a1a1aa; line-height: 1.6;">
                If you did not request a password reset, please ignore this email or reach out to <a href="mailto:support@tossatale.com" style="color: #f97316; text-decoration: none;">support@tossatale.com</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px; background-color: #121215; border-top: 1px solid #27272a; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #71717a; line-height: 1.5;">
                © {2026} Tossatale. Where stories live and breathe.<br>
                This is an automated security transmission.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        text_content = f"""
Hello {user_name},

Your Tossatale password reset verification code is: {otp_code}

This code is valid for 10 minutes. If you did not request this, please ignore this email.

— The Tossatale Team
https://tossatale.com
"""
        return EmailService.send_resend_email(
            to=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    @staticmethod
    def send_contact_confirmation_email(
        to_email: str,
        sender_name: str,
        inquiry_type: str = "General Inquiry",
    ) -> dict:
        """
        Send an acknowledgment email to a user who submitted a contact inquiry.
        """
        subject = f"We received your message — Tossatale {inquiry_type}"
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tossatale Message Received</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c0d0e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" max-width="540px" cellspacing="0" cellpadding="0" border="0" style="max-width: 540px; background-color: #18181b; border: 1px solid #27272a; border-radius: 20px; padding: 36px 40px;">
          <tr>
            <td align="center" style="border-bottom: 1px solid #27272a; padding-bottom: 20px;">
              <h1 style="margin: 0; font-size: 26px; color: #ffffff;">tossatale</h1>
            </td>
          </tr>
          <tr>
            <td style="padding-top: 28px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #e4e4e7;">Hello {sender_name},</p>
              <p style="margin: 0 0 20px 0; font-size: 15px; color: #a1a1aa; line-height: 1.6;">
                Thank you for reaching out to the Tossatale team regarding <strong>{inquiry_type}</strong>. We have received your inquiry and our editorial desk will review it shortly.
              </p>
              <p style="margin: 0 0 12px 0; font-size: 14px; color: #71717a;">
                Warm regards,<br>
                <strong>The Tossatale Editorial Desk</strong>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return EmailService.send_resend_email(
            to=to_email,
            subject=subject,
            html_content=html_content,
        )

    @staticmethod
    def send_editorial_status_email(
        to_email: str,
        writer_name: str,
        story_title: str,
        status: str,
        feedback: str = "",
    ) -> dict:
        """
        Notify a writer when their story is approved or returned for revisions.
        """
        is_approved = status.upper() == "PUBLISHED" or status.upper() == "APPROVED"
        subject = f"Editorial Update: '{story_title}' {'has been Published!' if is_approved else 'Needs Revisions'}"

        badge_color = "#10b981" if is_approved else "#f59e0b"
        badge_text = "PUBLISHED" if is_approved else "NEEDS REVISION"

        feedback_block = ""
        if feedback:
            feedback_block = f"""
            <div style="background-color: #09090b; border-left: 3px solid {badge_color}; border-radius: 8px; padding: 16px 20px; margin: 20px 0;">
              <p style="margin: 0 0 6px 0; font-size: 12px; color: #a1a1aa; font-weight: 700; text-transform: uppercase;">Editor Feedback:</p>
              <p style="margin: 0; font-size: 14px; color: #e4e4e7; line-height: 1.6; font-style: italic;">"{feedback}"</p>
            </div>
            """

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tossatale Editorial Update</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c0d0e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" max-width="540px" cellspacing="0" cellpadding="0" border="0" style="max-width: 540px; background-color: #18181b; border: 1px solid #27272a; border-radius: 20px; padding: 36px 40px;">
          <tr>
            <td align="center" style="border-bottom: 1px solid #27272a; padding-bottom: 20px;">
              <h1 style="margin: 0; font-size: 26px; color: #ffffff;">tossatale</h1>
            </td>
          </tr>
          <tr>
            <td style="padding-top: 28px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #e4e4e7;">Dear {writer_name},</p>
              <p style="margin: 0 0 20px 0; font-size: 15px; color: #a1a1aa; line-height: 1.6;">
                Our editorial review board has evaluated your submission: <strong>"{story_title}"</strong>.
              </p>
              
              <div style="display: inline-block; padding: 6px 14px; border-radius: 9999px; background-color: {badge_color}20; border: 1px solid {badge_color}50; color: {badge_color}; font-weight: 700; font-size: 12px; margin-bottom: 16px;">
                {badge_text}
              </div>

              {feedback_block}

              <p style="margin: 20px 0 0 0; font-size: 14px; color: #a1a1aa; line-height: 1.6;">
                You can view your story status and update your drafts directly in your <a href="https://tossatale.com/writer/stories" style="color: #f97316; font-weight: 600;">Writer Studio</a>.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return EmailService.send_resend_email(
            to=to_email,
            subject=subject,
            html_content=html_content,
        )
