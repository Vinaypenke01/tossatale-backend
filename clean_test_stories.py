import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.stories.models import Story

# Clean up duplicate test stories titled 'The Map Beneath the Floorboards'
deleted_count, _ = Story.objects.filter(title__icontains="The Map Beneath the Floorboards").delete()
print(f"Cleaned up {deleted_count} duplicate test story records.")
