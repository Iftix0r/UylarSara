from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Lucide icon name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

class Property(models.Model):
    PROPERTY_TYPES = (
        ('APARTMENT', 'Apartment'),
        ('HOUSE', 'House'),
        ('VILLA', 'Villa'),
        ('COMMERCIAL', 'Commercial'),
        ('NEW_CONSTRUCTION', 'New Construction'),
    )
    STATUS_CHOICES = (
        ('active',    'Faol'),
        ('inactive',  'Nofaol'),
        ('sold',      'Sotilgan'),
        ('rented',    'Ijarada'),
    )
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='properties', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name="Holat")

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=200)
    rooms = models.IntegerField()
    area = models.DecimalField(max_digits=8, decimal_places=2, help_text="Area in m²")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='properties')
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, default='APARTMENT')
    image = models.ImageField(upload_to='properties/', blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_gallery/')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

class Favorite(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'property')
        verbose_name = "Saralangan"
        verbose_name_plural = "Saralanganlar"

    def __str__(self):
        return f"{self.user.username} - {self.property.title}"

class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True, verbose_name='Telegram ID')
    telegram_username = models.CharField(max_length=100, blank=True)
    telegram_photo_url = models.URLField(max_length=500, blank=True, verbose_name='Telegram profil rasmi URL')
    bio = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signals to auto-create profile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
