import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarauylar.settings')
django.setup()

from base.models import Category, Property

def populate():
    # Clear existing data
    Property.objects.all().delete()
    Category.objects.all().delete()

    # Create User if not exists
    from django.contrib.auth.models import User
    admin_user, _ = User.objects.get_or_create(username='admin', is_staff=True, is_superuser=True)
    if _:
        admin_user.set_password('admin123')
        admin_user.save()

    # Create Categories
    categories_data = [
        {'name': 'Kvartiralar', 'icon': 'building-2'},
        {'name': 'Uylar', 'icon': 'home'},
        {'name': 'Villalar', 'icon': 'palmtree'},
        {'name': 'Tijorat', 'icon': 'briefcase'},
        {'name': 'Yangi qurilish', 'icon': 'factory'},
    ]

    created_categories = []
    for cat in categories_data:
        c = Category.objects.create(name=cat['name'], icon=cat['icon'])
        created_categories.append(c)

    # Create Properties
    locations = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan', 'Namangan', 'Fergana']
    titles = [
        '3 xonali zamonaviy kvartira - Chilonzor tumani',
        'Studio kvartira - Toshkent markazi',
        'Oilaviy uy - Andijon shahrida',
        'Penthouse - Toshkent City',
        'Zamonaviy uy - Samarqand',
        'Premium Villa - Bo\'stonliq',
        'Tijorat binosi - Yunusobod',
        'Yangi qurilish - Mirzo Ulug\'bek',
    ]

    # Tashkent areas with approx coordinates
    tashkent_areas = [
        ('Chilonzor tumani', 41.28, 69.20),
        ('Yunusobod tumani', 41.36, 69.28),
        ('Mirzo Ulug\'bek tumani', 41.32, 69.33),
        ('Shayxontohur tumani', 41.32, 69.23),
        ('Sergeli tumani', 41.23, 69.24),
        ('Yakkasaroy tumani', 41.28, 69.25),
    ]

    for i in range(50):
        area_name, lat, lng = random.choice(tashkent_areas)
        Property.objects.create(
            title=random.choice(titles),
            description="Premium sifatli materiallardan foydalanilgan, barcha qulayliklarga ega zamonaviy turar joy.",
            price=random.randint(30000, 500000),
            location=f"Toshkent, {area_name}",
            rooms=random.randint(1, 5),
            area=random.randint(30, 300),
            category=random.choice(created_categories),
            property_type=random.choice(['APARTMENT', 'HOUSE', 'VILLA', 'COMMERCIAL', 'NEW_CONSTRUCTION']),
            is_premium=random.choice([True, False, False]),
            latitude=lat + random.uniform(-0.01, 0.01),
            longitude=lng + random.uniform(-0.01, 0.01),
            owner=admin_user
        )

    print("Populated demo data successfully!")

if __name__ == '__main__':
    populate()
