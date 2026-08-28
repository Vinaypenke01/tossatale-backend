from django.core.management.base import BaseCommand
from common.services.email_service import EmailService


class Command(BaseCommand):
    help = "Dispatches a test verification email via Resend to verify configuration"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Recipient email address")

    def handle(self, *args, **options):
        to_email = options["email"]
        self.stdout.write(f"Sending test verification email to {to_email}...")
        try:
            res = EmailService.send_otp_email(
                to_email=to_email,
                otp_code="729415",
                user_name="Test User",
            )
            self.stdout.write(self.style.SUCCESS(f"Email dispatched successfully: {res}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email: {str(e)}"))
