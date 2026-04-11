import csv
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.urls import reverse
from django.http import HttpResponse
from django.utils import timezone
from .models import Category, Property, PropertyImage, Favorite, UserProfile

# ── Site branding (jazzmin handles visuals, keep index_title only) ────────────
admin.site.site_header  = "Sara Uylar Admin"
admin.site.site_title   = "Sara Uylar"
admin.site.index_title  = "Boshqaruv paneli"


# ── Patch index to inject stats ───────────────────────────────────────────────
_original_index = admin.site.__class__.index

def _custom_index(self, request, extra_context=None):
    extra_context = extra_context or {}
    extra_context['stats'] = {
        'total_properties':   Property.objects.count(),
        'premium_properties': Property.objects.filter(is_premium=True).count(),
        'total_users':        User.objects.count(),
        'total_favorites':    Favorite.objects.count(),
        'total_views':        Property.objects.aggregate(t=Sum('views_count'))['t'] or 0,
        'total_categories':   Category.objects.count(),
    }
    return _original_index(self, request, extra_context)

admin.site.__class__.index = _custom_index


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img(url, h=60, w=None, radius="6px"):
    style = f"height:{h}px;border-radius:{radius};object-fit:cover;"
    if w:
        style += f"width:{w}px;"
    return format_html('<img src="{}" style="{}">', url, style)


# ── CSV export ────────────────────────────────────────────────────────────────

@admin.action(description="📥 CSV ga eksport qilish")
def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="properties_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff')  # BOM for Excel UTF-8
    writer = csv.writer(response)
    writer.writerow(['ID', 'Sarlavha', 'Egasi', 'Kategoriya', 'Turi', 'Narx ($)',
                     'Xonalar', 'Maydon (m²)', 'Joylashuv', 'Premium', "Ko'rishlar", 'Sana'])
    for p in queryset.select_related('owner', 'category'):
        writer.writerow([
            p.pk, p.title,
            p.owner.username if p.owner else '',
            p.category.name, p.get_property_type_display(),
            p.price, p.rooms, p.area, p.location,
            'Ha' if p.is_premium else "Yo'q",
            p.views_count,
            p.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


# ── Property actions ──────────────────────────────────────────────────────────

@admin.action(description="⭐ Premium qilish")
def make_premium(modeladmin, request, queryset):
    updated = queryset.update(is_premium=True)
    modeladmin.message_user(request, f"{updated} ta e'lon premium qilindi.")

@admin.action(description="✖ Premiumni olib tashlash")
def remove_premium(modeladmin, request, queryset):
    updated = queryset.update(is_premium=False)
    modeladmin.message_user(request, f"{updated} ta e'londan premium olib tashlandi.")

@admin.action(description="🔄 Ko'rishlar sonini nolga tushirish")
def reset_views(modeladmin, request, queryset):
    updated = queryset.update(views_count=0)
    modeladmin.message_user(request, f"{updated} ta e'lon ko'rishlar soni nolga tushirildi.")


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
    model       = UserProfile
    can_delete  = False
    verbose_name = "Profil"
    fields      = ('phone_number', 'telegram_username', 'bio', 'avatar')
    extra       = 0


# ── User (extended) ───────────────────────────────────────────────────────────

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines         = (UserProfileInline,)
    list_display    = ('username', 'email', 'full_name', 'is_staff', 'is_active',
                       'date_joined', 'ads_count', 'favorites_count')
    list_filter     = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields   = ('username', 'email', 'first_name', 'last_name')
    ordering        = ('-date_joined',)
    list_per_page   = 25
    date_hierarchy  = 'date_joined'

    def full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or "—"
    full_name.short_description = "Ism"

    def ads_count(self, obj):
        count = obj.properties.count()
        if count:
            url = reverse('admin:base_property_changelist') + f'?owner__id__exact={obj.pk}'
            return format_html('<a href="{}" style="font-weight:600;color:#2563eb;">{} ta</a>', url, count)
        return format_html('<span style="color:#9ca3af;">0</span>')
    ads_count.short_description = "E'lonlar"

    def favorites_count(self, obj):
        count = obj.favorites.count()
        return format_html('<span style="color:#6b7280;">{} ta</span>', count)
    favorites_count.short_description = "Saralanganlar"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('properties', 'favorites')


# ── Category ──────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ('name', 'icon_badge', 'slug', 'property_count', 'view_listings')
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ('name',)
    ordering            = ('name',)
    list_per_page       = 20

    def icon_badge(self, obj):
        if obj.icon:
            return format_html(
                '<span style="background:#f0f4ff;padding:3px 10px;border-radius:20px;font-size:.85rem;">⚡ {}</span>',
                obj.icon
            )
        return "—"
    icon_badge.short_description = "Icon"

    def property_count(self, obj):
        count = obj.properties.count()
        url   = reverse('admin:base_property_changelist') + f'?category__id__exact={obj.pk}'
        color = "#16a34a" if count > 0 else "#9ca3af"
        return format_html(
            '<a href="{}" style="color:{};font-weight:600;">{} ta</a>', url, color, count
        )
    property_count.short_description = "E'lonlar"

    def view_listings(self, obj):
        url = reverse('admin:base_property_changelist') + f'?category__id__exact={obj.pk}'
        return format_html('<a href="{}" style="color:#2563eb;">→ Ko\'rish</a>', url)
    view_listings.short_description = ""

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(prop_count=Count('properties'))


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
    list_display         = ('thumb', 'title_link', 'owner_link', 'category',
                            'property_type', 'price_fmt', 'rooms', 'area',
                            'location', 'premium_badge', 'views_badge', 'created_at')
    list_display_links   = ('thumb', 'title_link')
    list_filter          = ('category', 'property_type', 'is_premium', 'created_at')
    list_editable        = ()   # premium inline edit olib tashlandi (list_display_links bilan conflict)
    search_fields        = ('title', 'location', 'description', 'owner__username')
    readonly_fields      = ('views_count', 'created_at', 'main_image_preview', 'site_link')
    ordering             = ('-created_at',)
    date_hierarchy       = 'created_at'
    actions              = [make_premium, remove_premium, reset_views, export_csv]
    inlines              = [PropertyImageInline]
    list_per_page        = 25
    save_on_top          = True
    show_full_result_count = True

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('owner', 'title', 'description', 'category', 'property_type', 'site_link')
        }),
        ("Narx va o'lchamlar", {
            'fields': ('price', 'rooms', 'area')
        }),
        ("Joylashuv", {
            'fields': ('location', 'latitude', 'longitude')
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
        return format_html('<span style="color:#9ca3af;font-size:.8rem;">—</span>')
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

    def price_fmt(self, obj):
        return format_html(
            '<span style="font-weight:600;color:#16a34a;">${:,.0f}</span>', obj.price
        )
    price_fmt.short_description = "Narx"
    price_fmt.admin_order_field = 'price'

    def premium_badge(self, obj):
        if obj.is_premium:
            return format_html(
                '<span style="background:#fbbf24;color:#78350f;padding:2px 8px;'
                'border-radius:20px;font-size:.75rem;font-weight:700;">⭐ Premium</span>'
            )
        return format_html('<span style="color:#9ca3af;">—</span>')
    premium_badge.short_description = "Premium"
    premium_badge.admin_order_field = 'is_premium'

    def views_badge(self, obj):
        color = "#2563eb" if obj.views_count > 50 else "#6b7280"
        return format_html(
            '<span style="color:{};font-weight:600;">👁 {}</span>', color, obj.views_count
        )
    views_badge.short_description = "Ko'rishlar"
    views_badge.admin_order_field = 'views_count'

    def main_image_preview(self, obj):
        if obj.image:
            return _img(obj.image.url, h=200, radius="10px")
        return "—"
    main_image_preview.short_description = "Joriy rasm"

    def site_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse('property_detail', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" style="color:#2563eb;">🔗 Saytda ko\'rish</a>', url
        )
    site_link.short_description = "Sayt havolasi"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'category').prefetch_related('images')


# ── Favorite ──────────────────────────────────────────────────────────────────

@admin.action(description="📥 Saralanganlarni CSV ga eksport")
def export_favorites_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="favorites.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Foydalanuvchi', "E'lon", 'Sana'])
    for f in queryset.select_related('user', 'property'):
        writer.writerow([f.user.username, f.property.title, f.created_at.strftime('%Y-%m-%d')])
    return response


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display    = ('user_link', 'property_link', 'property_price', 'created_at')
    list_filter     = ('created_at',)
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

    def property_price(self, obj):
        return format_html(
            '<span style="color:#16a34a;font-weight:600;">${:,.0f}</span>', obj.property.price
        )
    property_price.short_description = "Narx"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'property')


# ── UserProfile ───────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display       = ('avatar_thumb', 'user_link', 'phone_number', 'telegram_link', 'ads_count')
    list_display_links = ('avatar_thumb', 'user_link')
    search_fields      = ('user__username', 'user__email', 'phone_number', 'telegram_username')
    readonly_fields    = ('avatar_preview', 'ads_count')
    list_per_page      = 25

    fieldsets = (
        ("Foydalanuvchi", {'fields': ('user',)}),
        ("Kontakt",       {'fields': ('phone_number', 'telegram_username')}),
        ("Profil",        {'fields': ('avatar', 'avatar_preview', 'bio')}),
        ("Statistika",    {'fields': ('ads_count',), 'classes': ('collapse',)}),
    )

    def avatar_thumb(self, obj):
        if obj.avatar:
            return _img(obj.avatar.url, h=40, w=40, radius="50%")
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:40px;height:40px;border-radius:50%;background:#e5e7eb;font-size:1.1rem;">👤</span>'
        )
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
            return format_html(
                '<a href="https://t.me/{}" target="_blank" style="color:#0088cc;">@{}</a>',
                handle, handle
            )
        return "—"
    telegram_link.short_description = "Telegram"

    def ads_count(self, obj):
        count = obj.user.properties.count()
        if count:
            url = reverse('admin:base_property_changelist') + f'?owner__id__exact={obj.user.pk}'
            return format_html('<a href="{}" style="font-weight:600;">{} ta e\'lon</a>', url, count)
        return "0 ta e'lon"
    ads_count.short_description = "E'lonlar"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('user__properties')
