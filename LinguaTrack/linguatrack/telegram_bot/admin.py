from django.contrib import admin
from .models import TelegramUser, BotMessage, LinkToken


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


@admin.register(LinkToken)
class LinkTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_short', 'created_at', 'expires_at', 'is_used', 'is_valid_status', 'telegram_id']
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__username', 'token', 'telegram_id']
    readonly_fields = ['token', 'created_at']

    def token_short(self, obj):
        return f"{obj.token[:8]}..."

    token_short.short_description = 'Токен'

    def is_valid_status(self, obj):
        return obj.is_valid

    is_valid_status.short_description = 'Действителен'
    is_valid_status.boolean = True