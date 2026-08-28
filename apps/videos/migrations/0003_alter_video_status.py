# Generated migration for VideoStatus choices
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0002_video_category_name_video_cover_image_video_director_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='status',
            field=models.CharField(
                choices=[('IN_PRODUCTION', 'In Production'), ('COMPLETED', 'Completed'), ('RELEASED', 'Released'), ('ARCHIVED', 'Archived')],
                db_index=True,
                default='IN_PRODUCTION',
                max_length=50
            ),
        ),
    ]
