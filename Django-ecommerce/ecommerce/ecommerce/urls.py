# ecommerce/urls.py - главный файл URL
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Frontend URLs (основные страницы магазина)
    path('', include('shop.urls_frontend')),

    # Accounts URLs (профиль, вход, регистрация)
    path('', include('accounts.urls')),

    # API mobile URLs
    path('', include('shop.urls')),

    # Аутентификация API mobile
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
]

# Статические файлы в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)