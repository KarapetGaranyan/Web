# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Профиль пользователя
    path('profile/', views.profile, name='profile'),

    # Аутентификация
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]