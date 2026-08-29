# Generated for User model consent tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='consent_given',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='consent_given_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='terms_accepted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
