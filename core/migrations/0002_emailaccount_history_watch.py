from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailaccount',
            name='gmail_history_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='emailaccount',
            name='gmail_watch_expiration',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

