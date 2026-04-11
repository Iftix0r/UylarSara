from .models import Property, Category, Favorite
from django.contrib.auth.models import User


def panel_counts(request):
    if not request.path.startswith('/panel/'):
        return {}
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    return {
        'cnt_properties': Property.objects.count(),
        'cnt_users':      User.objects.count(),
        'cnt_favorites':  Favorite.objects.count(),
        'cnt_categories': Category.objects.count(),
    }
