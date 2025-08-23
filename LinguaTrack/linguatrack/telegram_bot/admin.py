from django.contrib import admin
from .models import TelegramUser, BotMessage

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'username', 'user', 'notifications_enabled', 'last_interaction']
    list_filter = ['notifications_enabled', 'is_active', 'created_at']
    search_fields = ['username', 'telegram_id', 'user__username']
    readonly_fields = ['telegram_id', 'last_interaction']

@admin.register(BotMessage)
class BotMessageAdmin(admin.ModelAdmin):
    list_display = ['telegram_user', 'message_type', 'sent_at']
    list_filter = ['message_type', 'sent_at']
    readonly_fields = ['sent_at']