from django.contrib import admin
from .models import Category, Property, PropertyImage

admin.site.site_header = "Sara Uylar - Boshqaruv Paneli"
admin.site.site_title = "Sara Uylar Admin"
admin.site.index_title = "Sara Uylar platformasiga xush kelibsiz"

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 3

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'rooms', 'is_premium', 'created_at')
    list_editable = ('is_premium',)
    list_filter = ('category', 'is_premium', 'property_type', 'created_at')
    search_fields = ('title', 'location', 'description')
    readonly_fields = ('created_at',)
    list_per_page = 20
    inlines = [PropertyImageInline]
    
    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('title', 'category', 'property_type', 'description')
        }),
        ('Narx va Joylashuv', {
            'fields': ('price', 'location')
        }),
        ('Xususiyatlar', {
            'fields': ('rooms', 'area', 'image', 'is_premium')
        }),
        ('Tizim', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
