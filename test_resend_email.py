"""
test_resend_email.py — Standalone Test Script for Resend Email API
Run with: python test_resend_email.py [recipient_email]
"""
import os
import sys
import json
from pathlib import Path

# Load .env file manually if django-environ is not loaded
def load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val

load_env_file()

import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "hello@tossatale.com")
RESEND_API_URL = "https://api.resend.com/emails"

def send_test_email(to_email: str):
    print("=" * 60)
    print("🚀 Tossatale Resend Email Dispatch Test")
    print("=" * 60)
    print(f"• Sender       : Tossatale <{DEFAULT_FROM_EMAIL}>")
    print(f"• Recipient    : {to_email}")
    print(f"• API Key      : {RESEND_API_KEY[:8]}...{RESEND_API_KEY[-4:]}")
    print("-" * 60)

    otp_code = "729415"
    user_name = "Vinay"

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tossatale Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c0d0e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0c0d0e; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" max-width="540px" cellspacing="0" cellpadding="0" border="0" style="max-width: 540px; background-color: #18181b; border: 1px solid #27272a; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
          <tr>
            <td style="padding: 36px 40px 20px 40px; text-align: center; border-bottom: 1px solid #27272a;">
              <h1 style="margin: 0; font-size: 26px; font-weight: 800; color: #ffffff;">tossatale</h1>
              <p style="margin: 6px 0 0 0; font-size: 13px; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
                Security Verification
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 36px 40px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #e4e4e7; line-height: 1.6;">Hello {user_name},</p>
              <p style="margin: 0 0 28px 0; font-size: 15px; color: #a1a1aa; line-height: 1.6;">
                We received a request to verify your Tossatale account credentials. Enter your 6-digit OTP code below to proceed:
              </p>
              <div style="background-color: #09090b; border: 1px solid #3f3f46; border-radius: 14px; padding: 24px 16px; text-align: center; margin-bottom: 28px;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: 800; letter-spacing: 10px; color: #f97316; display: inline-block;">
                  {otp_code}
                </span>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #71717a; font-weight: 500;">
                  ⏱ Valid for 10 minutes · Single use only
                </p>
              </div>
              <p style="margin: 0 0 12px 0; font-size: 14px; color: #a1a1aa; line-height: 1.6;">
                If you did not request this, you can safely ignore this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 40px; background-color: #121215; border-top: 1px solid #27272a; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #71717a;">© 2026 Tossatale. Where stories live and breathe.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    payload = {
        "from": f"Tossatale <{DEFAULT_FROM_EMAIL}>",
        "to": [to_email],
        "subject": f"Your Tossatale Verification Code: {otp_code}",
        "html": html_content,
        "text": f"Hello {user_name},\n\nYour Tossatale verification code is: {otp_code}\n\nValid for 10 minutes.",
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    print("📡 Sending HTTP request to Resend API...")
    try:
        response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("\n🎉 SUCCESS! Email dispatched via Resend API.")
            print(f"• Resend Email ID : {data.get('id')}")
            print(f"• Delivered To    : {to_email}")
            print("• Please check your inbox / spam folder!")
        else:
            print("\n❌ API ERROR from Resend:")
            print(response.text)
    except Exception as e:
        print(f"\n❌ Network / Execution Exception: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "delivered@resend.dev"
    send_test_email(target)
