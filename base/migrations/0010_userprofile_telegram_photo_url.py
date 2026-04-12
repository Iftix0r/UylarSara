from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0009_userprofile_telegram_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='telegram_photo_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='Telegram profil rasmi URL'),
        ),
    ]
