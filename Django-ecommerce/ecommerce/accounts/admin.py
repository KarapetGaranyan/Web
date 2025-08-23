# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('phone', 'birth_date', 'address', 'city', 'postal_code', 'avatar')


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_phone')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')

    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') else ''

    get_phone.short_description = 'Телефон'


# Перерегистрируем User с новым админом
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city']
    list_filter = ['city']
    search_fields = ['user__username', 'user__email', 'phone']

    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Контактная информация', {
            'fields': ('phone', 'birth_date', 'avatar')
        }),
        ('Адрес', {
            'fields': ('address', 'city', 'postal_code')
        }),
    )