from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_property_views_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='status',
            field=models.CharField(
                choices=[
                    ('active',   'Faol'),
                    ('inactive', 'Nofaol'),
                    ('sold',     'Sotilgan'),
                    ('rented',   'Ijarada'),
                ],
                default='active',
                max_length=10,
                verbose_name='Holat',
            ),
        ),
    ]
