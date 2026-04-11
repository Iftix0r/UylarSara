from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from django.db.models import Sum
from .models import Property, Favorite, Category


class SaraUylarAdminSite(AdminSite):
    site_header = "Sara Uylar Admin"
    site_title  = "Sara Uylar"
    index_title = "Boshqaruv paneli"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_properties':  Property.objects.count(),
            'premium_properties': Property.objects.filter(is_premium=True).count(),
            'total_users':       User.objects.count(),
            'total_favorites':   Favorite.objects.count(),
            'total_views':       Property.objects.aggregate(t=Sum('views_count'))['t'] or 0,
            'total_categories':  Category.objects.count(),
        }
        return super().index(request, extra_context)
