from django.urls import path
from . import views

app_name = 'telegram_bot'

urlpatterns = [
    path('webhook/', views.webhook, name='webhook'),
    path('set-webhook/', views.set_webhook, name='set_webhook'),
    path('info/', views.bot_info, name='bot_info'),
    path('link/', views.link_telegram, name='link_telegram'),
    path('link/confirm/<str:token>/', views.confirm_link, name='confirm_link'),
    path('unlink/', views.unlink_telegram, name='unlink_telegram'),  # Новый URL
]