from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.urls import reverse
from .models import Category, Property, PropertyImage, Favorite, UserProfile

# ── Site branding ─────────────────────────────────────────────────────────────
admin.site.site_header  = mark_safe('<span style="font-size:1.3rem;font-weight:700;">🏠 Sara Uylar Admin</span>')
admin.site.site_title   = "Sara Uylar"
admin.site.index_title  = "Boshqaruv paneli"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img(url, h=60, w=None, radius="6px"):
    style = f"height:{h}px;border-radius:{radius};object-fit:cover;"
    if w:
        style += f"width:{w}px;"
    return format_html('<img src="{}" style="{}">', url, style)


# ── Inlines ───────────────────────────────────────────────────────────────────

class PropertyImageInline(admin.TabularInline):
    model        = PropertyImage
    extra        = 1
    fields       = ('image', 'order', 'preview')
    readonly_fields = ('preview',)
    show_change_link = True

    def preview(self, obj):
        return _img(obj.image.url) if obj.image else "—"
    preview.short_description = "Ko'rinish"


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


# ── Property actions ──────────────────────────────────────────────────────────

@admin.action(description="✅ Premium qilish")
def make_premium(modeladmin, request, queryset):
    queryset.update(is_premium=True)

@admin.action(description="❌ Premiumni olib tashlash")
def remove_premium(modeladmin, request, queryset):
    queryset.update(is_premium=False)

@admin.action(description="🔄 Ko'rishlar sonini nolga tushirish")
def reset_views(modeladmin, request, queryset):
    queryset.update(views_count=0)


# ── Property ──────────────────────────────────────────────────────────────────

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display         = ('thumb', 'title_link', 'owner_link', 'category',
                            'property_type', 'price_fmt', 'rooms', 'area',
                            'location', 'premium_badge', 'views_badge', 'created_at')
    list_display_links   = ('thumb', 'title_link')
    list_filter          = ('category', 'property_type', 'is_premium', 'created_at')
    search_fields        = ('title', 'location', 'description', 'owner__username')
    readonly_fields      = ('views_count', 'created_at', 'main_image_preview')
    ordering             = ('-created_at',)
    date_hierarchy       = 'created_at'
    actions              = [make_premium, remove_premium, reset_views]
    inlines              = [PropertyImageInline]
    list_per_page        = 25
    save_on_top          = True
    show_full_result_count = True

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('owner', 'title', 'description', 'category', 'property_type')
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

    # ── Custom columns ────────────────────────────────────────────────────────

    def thumb(self, obj):
        if obj.image:
            return _img(obj.image.url, h=48, w=64)
        first = obj.images.first()
        if first:
            return _img(first.image.url, h=48, w=64)
        return format_html('<span style="color:#9ca3af;font-size:.8rem;">Rasm yo\'q</span>')
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
            '<span style="font-weight:600;color:#16a34a;">${:,.0f}</span>',
            obj.price
        )
    price_fmt.short_description = "Narx"
    price_fmt.admin_order_field = 'price'

    def premium_badge(self, obj):
        if obj.is_premium:
            return format_html(
                '<span style="background:#fbbf24;color:#78350f;padding:2px 8px;'
                'border-radius:20px;font-size:.75rem;font-weight:700;">⭐ Premium</span>'
            )
        return format_html('<span style="color:#9ca3af;font-size:.8rem;">—</span>')
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'category').prefetch_related('images')


# ── Favorite ──────────────────────────────────────────────────────────────────

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display  = ('user_link', 'property_link', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('user__username', 'property__title')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'
    list_per_page   = 30

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "Foydalanuvchi"

    def property_link(self, obj):
        url = reverse('admin:base_property_change', args=[obj.property.pk])
        return format_html('<a href="{}">{}</a>', url, obj.property.title)
    property_link.short_description = "E'lon"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'property')


# ── UserProfile ───────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display    = ('avatar_thumb', 'user_link', 'phone_number', 'telegram_link', 'ads_count')
    list_display_links = ('avatar_thumb', 'user_link')
    search_fields   = ('user__username', 'user__email', 'phone_number', 'telegram_username')
    readonly_fields = ('avatar_preview', 'ads_count')
    list_per_page   = 25

    fieldsets = (
        ("Foydalanuvchi", {
            'fields': ('user',)
        }),
        ("Kontakt", {
            'fields': ('phone_number', 'telegram_username')
        }),
        ("Profil", {
            'fields': ('avatar', 'avatar_preview', 'bio')
        }),
        ("Statistika", {
            'fields': ('ads_count',),
            'classes': ('collapse',)
        }),
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
        if obj.avatar:
            return _img(obj.avatar.url, h=120, w=120, radius="50%")
        return "—"
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
