from django.core.management.base import BaseCommand
from apps.analytics.services import TrendingService


class Command(BaseCommand):
    help = "Recalculate trending scores for all published stories"

    def handle(self, *args, **options):
        self.stdout.write("Calculating trending scores...")
        try:
            top_stories = TrendingService.update_all_trending_scores()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated trending scores. Top {len(top_stories)} stories cached.")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error updating trending scores: {str(e)}"))
