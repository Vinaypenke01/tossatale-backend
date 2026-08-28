"""
Django management command to reconcile denormalized counters on Story and WriterProfile models.
Usage: python manage.py reconcile_counters
"""
from django.core.management.base import BaseCommand
from apps.analytics.services import AnalyticsService
from apps.stories.models import Story
from apps.writers.models import WriterProfile


class Command(BaseCommand):
    help = "Recalculates and synchronizes denormalized engagement counters on stories and writer profiles"

    def handle(self, *args, **options):
        self.stdout.write("Reconciling story and writer counters...")
        try:
            AnalyticsService.reconcile_all_counters()
            story_count = Story.objects.count()
            writer_count = WriterProfile.all_objects.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully reconciled counters for {story_count} stories and {writer_count} writers."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reconciling counters: {str(e)}"))
