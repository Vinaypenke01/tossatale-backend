# Generated migration for FAQItem BaseModel refactoring
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_config', '0002_faqitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='faqitem',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='faqitem',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
