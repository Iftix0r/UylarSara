from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('seller/<str:username>/', views.seller_profile, name='seller_profile'),
    path('add/', views.add_property, name='add_property'),
    path('signup/', views.signup, name='signup'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorite/toggle/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    path('profile/', views.profile, name='profile'),
    path('about/', views.about, name='about'),
    path('help/', views.help_page, name='help'),
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-whisper/', views.ai_whisper, name='ai_whisper'),
    path('ai-tts/', views.ai_tts, name='ai_tts'),
    path('set-city/<str:city>/', views.set_city, name='set_city'),
    path('set-language/<str:lang>/', views.set_language, name='set_language'),
    path('accounts/', include('django.contrib.auth.urls')),
]
