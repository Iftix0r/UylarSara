from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0009_userprofile_telegram_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Tasdiq kutilmoqda'),
                    ('active', 'Faol'),
                    ('inactive', 'Nofaol'),
                    ('sold', 'Sotilgan'),
                    ('rented', 'Ijarada'),
                ],
                default='pending',
                max_length=10,
                verbose_name='Holat',
            ),
        ),
    ]
