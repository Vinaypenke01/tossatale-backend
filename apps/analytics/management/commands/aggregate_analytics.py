from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.stories.models import Story
from apps.analytics.services import AnalyticsService


class Command(BaseCommand):
    help = "Aggregate daily analytics for stories, writers, and platform"

    def handle(self, *args, **options):
        yesterday = date.today() - timedelta(days=1)
        self.stdout.write(f"Aggregating analytics for {yesterday}...")
        try:
            AnalyticsService.aggregate_all_stories_for_date(yesterday)
            count = Story.objects.filter(status="PUBLISHED").count()
            AnalyticsService.aggregate_writer_day(yesterday)
            AnalyticsService.aggregate_platform_day(yesterday)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully aggregated daily analytics for {count} stories and all writers.")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error aggregating analytics: {str(e)}"))
