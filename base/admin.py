import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Q
from django.urls import reverse
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import Category, Property, PropertyImage, Favorite, UserProfile

# ── Site config ───────────────────────────────────────────────────────────────
admin.site.site_header = "Sara Uylar Admin"
admin.site.site_title  = "Sara Uylar"
admin.site.index_title = "Boshqaruv paneli"

# ── Dashboard stats patch ─────────────────────────────────────────────────────
_orig_index = admin.site.__class__.index

def _custom_index(self, request, extra_context=None):
    extra_context = extra_context or {}
    week_ago = now() - timedelta(days=7)
    from django.db import connection
    has_status = 'status' in [col.name for col in connection.introspection.get_table_description(connection.cursor(), 'base_property')]

    stats = {
        'total_properties':   Property.objects.count(),
        'premium_properties': Property.objects.filter(is_premium=True).count(),
        'active_properties':  Property.objects.filter(status='active').count() if has_status else '—',
        'sold_properties':    Property.objects.filter(status='sold').count() if has_status else '—',
        'total_users':        User.objects.count(),
        'new_users_week':     User.objects.filter(date_joined__gte=week_ago).count(),
        'total_favorites':    Favorite.objects.count(),
        'total_views':        Property.objects.aggregate(t=Sum('views_count'))['t'] or 0,
        'total_categories':   Category.objects.count(),
        'new_props_week':     Property.objects.filter(created_at__gte=week_ago).count(),
    }
    extra_context['stats'] = stats
    return _orig_index(self, request, extra_context)

admin.site.__class__.index = _custom_index

# ── Helpers ───────────────────────────────────────────────────────────────────
def _img(url, h=60, w=None, radius="6px"):
    style = f"height:{h}px;border-radius:{radius};object-fit:cover;"
    if w:
        style += f"width:{w}px;"
    return format_html('<img src="{}" style="{}">', url, style)

STATUS_COLORS = {
    'active':   ('#dcfce7', '#166534'),
    'inactive': ('#f3f4f6', '#374151'),
    'sold':     ('#fee2e2', '#991b1b'),
    'rented':   ('#dbeafe', '#1e40af'),
}

# ── Actions ───────────────────────────────────────────────────────────────────

@admin.action(description="📥 CSV ga eksport")
def export_properties_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="properties_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['ID', 'Sarlavha', 'Egasi', 'Kategoriya', 'Turi', 'Holat',
                     'Narx ($)', 'Xonalar', 'Maydon (m²)', 'Joylashuv', 'Premium', "Ko'rishlar", 'Sana'])
    for p in queryset.select_related('owner', 'category'):
        writer.writerow([
            p.pk, p.title,
            p.owner.username if p.owner else '',
            p.category.name, p.get_property_type_display(),
            p.get_status_display(),
            p.price, p.rooms, p.area, p.location,
            'Ha' if p.is_premium else "Yo'q",
            p.views_count,
            p.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response

@admin.action(description="⭐ Premium qilish")
def make_premium(modeladmin, request, queryset):
    n = queryset.update(is_premium=True)
    modeladmin.message_user(request, f"{n} ta e'lon premium qilindi.")

@admin.action(description="✖ Premiumni olib tashlash")
def remove_premium(modeladmin, request, queryset):
    n = queryset.update(is_premium=False)
    modeladmin.message_user(request, f"{n} ta e'londan premium olib tashlandi.")

@admin.action(description="🔄 Ko'rishlarni nolga tushirish")
def reset_views(modeladmin, request, queryset):
    n = queryset.update(views_count=0)
    modeladmin.message_user(request, f"{n} ta e'lon ko'rishlar soni nolga tushirildi.")

@admin.action(description="✅ Faol qilish")
def mark_active(modeladmin, request, queryset):
    n = queryset.update(status='active')
    modeladmin.message_user(request, f"{n} ta e'lon faol qilindi.")

@admin.action(description="🔴 Nofaol qilish")
def mark_inactive(modeladmin, request, queryset):
    n = queryset.update(status='inactive')
    modeladmin.message_user(request, f"{n} ta e'lon nofaol qilindi.")

@admin.action(description="🏷 Sotilgan deb belgilash")
def mark_sold(modeladmin, request, queryset):
    n = queryset.update(status='sold')
    modeladmin.message_user(request, f"{n} ta e'lon sotilgan deb belgilandi.")

@admin.action(description="📧 Egasiga email yuborish")
def email_owners(modeladmin, request, queryset):
    sent = 0
    for prop in queryset.select_related('owner'):
        if prop.owner and prop.owner.email:
            try:
                send_mail(
                    subject=f"Sara Uylar: '{prop.title}' e'loningiz haqida",
                    message=f"Hurmatli {prop.owner.get_full_name() or prop.owner.username},\n\n"
                            f"'{prop.title}' e'loningiz admin tomonidan ko'rib chiqildi.\n\n"
                            f"Sara Uylar jamoasi",
                    from_email=django_settings.DEFAULT_FROM_EMAIL if hasattr(django_settings, 'DEFAULT_FROM_EMAIL') else 'noreply@sarauylar.uz',
                    recipient_list=[prop.owner.email],
                    fail_silently=True,
                )
                sent += 1
            except Exception:
                pass
    modeladmin.message_user(request, f"{sent} ta egaga email yuborildi.")

@admin.action(description="🚫 Foydalanuvchini bloklash")
def block_users(modeladmin, request, queryset):
    n = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{n} ta foydalanuvchi bloklandi.", level='warning')

@admin.action(description="✅ Foydalanuvchini faollashtirish")
def unblock_users(modeladmin, request, queryset):
    n = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{n} ta foydalanuvchi faollashtirildi.")

@admin.action(description="📥 Saralanganlarni CSV ga eksport")
def export_favorites_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="favorites.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Foydalanuvchi', 'Email', "E'lon", 'Narx', 'Sana'])
    for f in queryset.select_related('user', 'property'):
        writer.writerow([
            f.user.username, f.user.email,
            f.property.title, f.property.price,
            f.created_at.strftime('%Y-%m-%d'),
        ])
    return response

# ── Inlines ───────────────────────────────────────────────────────────────────

class PropertyImageInline(admin.TabularInline):
    model            = PropertyImage
    extra            = 1
    fields           = ('image', 'order', 'preview')
    readonly_fields  = ('preview',)
    show_change_link = True

    def preview(self, obj):
        return _img(obj.image.url) if obj.image else "—"
    preview.short_description = "Ko'rinish"


class UserProfileInline(admin.StackedInline):
    model        = UserProfile
    can_delete   = False
    verbose_name = "Profil"
    fields       = ('phone_number', 'telegram_username', 'telegram_id', 'bio', 'avatar')
    readonly_fields = ('telegram_id',)
    extra        = 0


# ── User ──────────────────────────────────────────────────────────────────────

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines       = (UserProfileInline,)
    list_display  = ('avatar_col', 'username', 'email', 'full_name', 'active_badge',
                     'is_staff', 'date_joined', 'last_login_fmt', 'ads_count', 'fav_count')
    list_display_links = ('avatar_col', 'username')
    list_filter   = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    list_per_page = 25
    date_hierarchy = 'date_joined'
    actions       = [block_users, unblock_users]

    def avatar_col(self, obj):
        try:
            if obj.profile.avatar:
                return _img(obj.profile.avatar.url, h=36, w=36, radius="50%")
            if obj.profile.telegram_photo_url:
                return format_html('<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">', obj.profile.telegram_photo_url)
        except Exception:
            pass
        initials = (obj.first_name[:1] + obj.last_name[:1]).upper() or obj.username[:2].upper()
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:36px;height:36px;border-radius:50%;background:#2563eb;color:#fff;'
            'font-weight:700;font-size:.8rem;">{}</span>', initials
        )
    avatar_col.short_description = ""

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "—"
    full_name.short_description = "Ism"

    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#16a34a;font-weight:600;">● Faol</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;">● Bloklangan</span>')
    active_badge.short_description = "Holat"
    active_badge.admin_order_field = 'is_active'

    def last_login_fmt(self, obj):
        if obj.last_login:
            delta = now() - obj.last_login
            if delta.days == 0:
                return format_html('<span style="color:#16a34a;">Bugun</span>')
            elif delta.days <= 7:
                return format_html('<span style="color:#f59e0b;">{} kun oldin</span>', delta.days)
            return format_html('<span style="color:#9ca3af;">{}</span>', obj.last_login.strftime('%d.%m.%Y'))
        return "—"
    last_login_fmt.short_description = "Oxirgi kirish"

    def ads_count(self, obj):
        count = obj.properties.count()
        if count:
            url = reverse('admin:base_property_changelist') + f'?owner__id__exact={obj.pk}'
            return format_html('<a href="{}" style="font-weight:600;color:#2563eb;">{}</a>', url, count)
        return format_html('<span style="color:#9ca3af;">0</span>')
    ads_count.short_description = "E'lonlar"

    def fav_count(self, obj):
        return format_html('<span style="color:#dc2626;">♥ {}</span>', obj.favorites.count())
    fav_count.short_description = "Saralanganlar"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('properties', 'favorites', 'profile')

# ── Category ──────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ('name', 'icon_badge', 'slug', 'property_count', 'active_count', 'view_link')
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ('name',)
    ordering            = ('name',)
    list_per_page       = 20

    def icon_badge(self, obj):
        if obj.icon:
            return format_html(
                '<span style="background:#f0f4ff;padding:3px 10px;border-radius:20px;font-size:.85rem;">⚡ {}</span>',
                obj.icon)
        return "—"
    icon_badge.short_description = "Icon"

    def property_count(self, obj):
        count = obj.properties.count()
        url = reverse('admin:base_property_changelist') + f'?category__id__exact={obj.pk}'
        color = "#16a34a" if count > 0 else "#9ca3af"
        return format_html('<a href="{}" style="color:{};font-weight:600;">{} ta</a>', url, color, count)
    property_count.short_description = "Jami"

    def active_count(self, obj):
        count = obj.properties.filter(status='active').count()
        return format_html('<span style="color:#16a34a;font-weight:600;">{} faol</span>', count)
    active_count.short_description = "Faol"

    def view_link(self, obj):
        url = reverse('admin:base_property_changelist') + f'?category__id__exact={obj.pk}'
        return format_html('<a href="{}">→ Ko\'rish</a>', url)
    view_link.short_description = ""


# ── PropertyImage ─────────────────────────────────────────────────────────────

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display  = ('property_link', 'order', 'preview')
    list_filter   = ('property__category',)
    search_fields = ('property__title',)
    ordering      = ('property', 'order')
    list_per_page = 30

    def preview(self, obj):
        return _img(obj.image.url) if obj.image else "—"
    preview.short_description = "Rasm"

    def property_link(self, obj):
        url = reverse('admin:base_property_change', args=[obj.property.pk])
        return format_html('<a href="{}">{}</a>', url, obj.property.title)
    property_link.short_description = "E'lon"

# ── Property ──────────────────────────────────────────────────────────────────

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display       = ('thumb', 'title_link', 'owner_link', 'category',
                          'property_type', 'price_fmt',
                          'rooms', 'area', 'premium_badge', 'views_badge', 'created_at')
    list_display_links = ('thumb', 'title_link')
    list_filter        = ('category', 'property_type', 'is_premium', 'created_at')
    search_fields      = ('title', 'location', 'description', 'owner__username')
    readonly_fields    = ('views_count', 'created_at', 'main_image_preview', 'site_link', 'map_preview')
    ordering           = ('-created_at',)
    date_hierarchy     = 'created_at'
    list_per_page      = 25
    save_on_top        = True
    show_full_result_count = True
    actions            = [make_premium, remove_premium, reset_views,
                          email_owners, export_properties_csv]
    inlines            = [PropertyImageInline]

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('owner', 'title', 'description', 'category', 'property_type', 'site_link')
        }),
        ("Narx va o'lchamlar", {
            'fields': ('price', 'rooms', 'area')
        }),
        ("Joylashuv", {
            'fields': ('location', 'latitude', 'longitude', 'map_preview')
        }),
        ("Rasm va holat", {
            'fields': ('image', 'main_image_preview', 'is_premium')
        }),
        ("Statistika", {
            'fields': ('views_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def thumb(self, obj):
        if obj.image:
            return _img(obj.image.url, h=48, w=64)
        first = obj.images.first()
        if first:
            return _img(first.image.url, h=48, w=64)
        return format_html('<span style="color:#9ca3af;">—</span>')
    thumb.short_description = ""

    def title_link(self, obj):
        return obj.title
    title_link.short_description = "Sarlavha"

    def owner_link(self, obj):
        if not obj.owner:
            return "—"
        url = reverse('admin:auth_user_change', args=[obj.owner.pk])
        return format_html('<a href="{}">{}</a>', url, obj.owner.username)
    owner_link.short_description = "Egasi"

    def status_badge(self, obj):
        status = getattr(obj, 'status', None)
        if not status:
            return "—"
        bg, fg = STATUS_COLORS.get(status, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:20px;'
            'font-size:.75rem;font-weight:700;">{}</span>',
            bg, fg, obj.get_status_display()
        )
    status_badge.short_description = "Holat"
    status_badge.admin_order_field = 'status'

    def price_fmt(self, obj):
        return format_html('<span style="font-weight:600;color:#16a34a;">${:,.0f}</span>', obj.price)
    price_fmt.short_description = "Narx"
    price_fmt.admin_order_field = 'price'

    def premium_badge(self, obj):
        if obj.is_premium:
            return format_html(
                '<span style="background:#fbbf24;color:#78350f;padding:2px 8px;'
                'border-radius:20px;font-size:.75rem;font-weight:700;">⭐ Premium</span>')
        return "—"
    premium_badge.short_description = "Premium"
    premium_badge.admin_order_field = 'is_premium'

    def views_badge(self, obj):
        color = "#2563eb" if obj.views_count > 50 else "#6b7280"
        return format_html('<span style="color:{};font-weight:600;">👁 {}</span>', color, obj.views_count)
    views_badge.short_description = "Ko'rishlar"
    views_badge.admin_order_field = 'views_count'

    def main_image_preview(self, obj):
        return _img(obj.image.url, h=200, radius="10px") if obj.image else "—"
    main_image_preview.short_description = "Joriy rasm"

    def site_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse('property_detail', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">🔗 Saytda ko\'rish</a>', url)
    site_link.short_description = "Havola"

    def map_preview(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<iframe width="100%" height="250" frameborder="0" style="border-radius:10px;" '
                'src="https://maps.google.com/maps?q={},{}&z=15&output=embed"></iframe>',
                obj.latitude, obj.longitude
            )
        return format_html('<span style="color:#9ca3af;">Koordinatalar kiritilmagan</span>')
    map_preview.short_description = "Xarita"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'category').prefetch_related('images')

# ── Favorite ──────────────────────────────────────────────────────────────────

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display    = ('user_link', 'property_link', 'property_status', 'property_price', 'created_at')
    list_filter     = ('created_at', 'property__category')
    search_fields   = ('user__username', 'property__title')
    ordering        = ('-created_at',)
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'
    list_per_page   = 30
    actions         = [export_favorites_csv]

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "Foydalanuvchi"

    def property_link(self, obj):
        url = reverse('admin:base_property_change', args=[obj.property.pk])
        return format_html('<a href="{}">{}</a>', url, obj.property.title)
    property_link.short_description = "E'lon"

    def property_status(self, obj):
        status = getattr(obj.property, 'status', None)
        if not status:
            return "—"
        bg, fg = STATUS_COLORS.get(status, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:20px;font-size:.75rem;">{}</span>',
            bg, fg, obj.property.get_status_display()
        )
    property_status.short_description = "Holat"

    def property_price(self, obj):
        return format_html('<span style="color:#16a34a;font-weight:600;">${:,.0f}</span>', obj.property.price)
    property_price.short_description = "Narx"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'property')


# ── UserProfile ───────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display       = ('avatar_thumb', 'user_link', 'phone_number', 'telegram_link', 'telegram_id_col', 'ads_count', 'joined')
    list_display_links = ('avatar_thumb', 'user_link')
    search_fields      = ('user__username', 'user__email', 'phone_number', 'telegram_username', 'telegram_id')
    readonly_fields    = ('avatar_preview', 'ads_count', 'joined')
    list_per_page      = 25

    fieldsets = (
        ("Foydalanuvchi", {'fields': ('user',)}),
        ("Kontakt",       {'fields': ('phone_number', 'telegram_username', 'telegram_id')}),
        ("Profil",        {'fields': ('avatar', 'avatar_preview', 'bio')}),
        ("Statistika",    {'fields': ('ads_count', 'joined'), 'classes': ('collapse',)}),
    )

    def avatar_thumb(self, obj):
        if obj.avatar:
            return _img(obj.avatar.url, h=38, w=38, radius="50%")
        if obj.telegram_photo_url:
            return format_html('<img src="{}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;">', obj.telegram_photo_url)
        initials = (obj.user.first_name[:1] + obj.user.last_name[:1]).upper() or obj.user.username[:2].upper()
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:38px;height:38px;border-radius:50%;background:#2563eb;color:#fff;'
            'font-weight:700;font-size:.8rem;">{}</span>', initials)
    avatar_thumb.short_description = ""

    def avatar_preview(self, obj):
        return _img(obj.avatar.url, h=120, w=120, radius="50%") if obj.avatar else "—"
    avatar_preview.short_description = "Avatar"

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="font-weight:600;">{}</a>', url, obj.user.username)
    user_link.short_description = "Foydalanuvchi"

    def telegram_link(self, obj):
        if obj.telegram_username:
            handle = obj.telegram_username.lstrip('@')
            return format_html('<a href="https://t.me/{}" target="_blank" style="color:#0088cc;">@{}</a>', handle, handle)
        return "—"
    telegram_link.short_description = "Telegram"

    def telegram_id_col(self, obj):
        if obj.telegram_id:
            return format_html('<span style="font-family:monospace;color:#6b7280;">{}</span>', obj.telegram_id)
        return "—"
    telegram_id_col.short_description = "Telegram ID"

    def ads_count(self, obj):
        count = obj.user.properties.count()
        if count:
            url = reverse('admin:base_property_changelist') + f'?owner__id__exact={obj.user.pk}'
            return format_html('<a href="{}" style="font-weight:600;">{} ta e\'lon</a>', url, count)
        return "0 ta e'lon"
    ads_count.short_description = "E'lonlar"

    def joined(self, obj):
        return obj.user.date_joined.strftime('%d.%m.%Y')
    joined.short_description = "Ro'yxatdan o'tgan"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('user__properties')
