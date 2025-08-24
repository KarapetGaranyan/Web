from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from cards.views import register_view, custom_login_view


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('cards:card_list')
    return redirect('login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('cards/', include('cards.urls')),
    path('', home_redirect, name='home'),

    # Аутентификация
    path('login/', custom_login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Импортируем представления только если они существуют
try:
    from cards.views import register_view, custom_login_view
    CUSTOM_AUTH = True
except ImportError:
    CUSTOM_AUTH = False

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('cards:card_list')
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cards/', include('cards.urls')),
    path('', home_redirect, name='home'),
]

# Добавляем URL для аутентификации
if CUSTOM_AUTH:
    urlpatterns += [
        path('login/', custom_login_view, name='login'),
        path('register/', register_view, name='register'),
    ]
else:
    urlpatterns += [
        path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
        path('register/', auth_views.LoginView.as_view(template_name='registration/register.html'), name='register'),
    ]

urlpatterns += [
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]

# Добавляем Telegram URL только если приложение существует
try:
    urlpatterns.append(path('telegram/', include('telegram_bot.urls')))
except:
    pass

# Медиа файлы
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)