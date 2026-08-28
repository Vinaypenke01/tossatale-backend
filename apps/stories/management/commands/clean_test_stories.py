from django.core.management.base import BaseCommand
from apps.stories.models import Story


class Command(BaseCommand):
    help = "Cleans up test stories from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--title",
            type=str,
            default="The Map Beneath the Floorboards",
            help="Title pattern to match and delete",
        )

    def handle(self, *args, **options):
        title = options["title"]
        self.stdout.write(f"Cleaning up test stories matching '{title}'...")
        deleted_count, _ = Story.objects.filter(title__icontains=title).delete()
        self.stdout.write(
            self.style.SUCCESS(f"Cleaned up {deleted_count} test story records.")
        )
