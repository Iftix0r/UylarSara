from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Property, PropertyImage, Favorite, UserProfile

# Admin panel sarlavhalari (Jazzmin buni ishlatsa ham, bu yerda ham turgani yaxshi)
admin.site.site_header = "Sara Uylar - Boshqaruv Paneli"
admin.site.site_title = "Sara Uylar Admin"
admin.site.index_title = "Boshqaruv markaziga xush kelibsiz"

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    readonly_fields = ('display_image',)
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="70" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "Rasm yo'q"
    display_image.short_description = "Rasm ko'rinishi"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('display_thumbnail', 'title', 'category', 'price_formatted', 'location', 'is_premium', 'created_at')
    list_display_links = ('display_thumbnail', 'title')
    list_editable = ('is_premium',)
    list_filter = ('category', 'property_type', 'is_premium', 'created_at')
    search_fields = ('title', 'location', 'description')
    readonly_fields = ('views_count', 'created_at')
    inlines = [PropertyImageInline]
    
    def display_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="45" style="object-fit: cover; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />', obj.image.url)
        return format_html('<div style="width: 60px; height: 45px; background: #eee; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 10px;">N/A</div>')
    display_thumbnail.short_description = "Rasm"

    def price_formatted(self, obj):
        return format_html('<b style="color: #28a745;">${:,.0f}</b>', obj.price)
    price_formatted.short_description = "Narxi"

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': (('owner', 'category'), 'title', 'description', 'property_type')
        }),
        ('Narx va Joylashuv', {
            'fields': (('price', 'location'), ('latitude', 'longitude'))
        }),
        ('Xususiyatlar', {
            'fields': (('rooms', 'area'), 'image', 'is_premium')
        }),
        ('Statistika va Vaqt', {
            'fields': (('views_count', 'created_at'),),
            'classes': ('collapse',),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'telegram_username')
    search_fields = ('user__username', 'phone_number', 'telegram_username')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('created_at',)
