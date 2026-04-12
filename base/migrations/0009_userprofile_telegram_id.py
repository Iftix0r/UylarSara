from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_property_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='telegram_id',
            field=models.BigIntegerField(null=True, blank=True, unique=True, verbose_name='Telegram ID'),
        ),
    ]
