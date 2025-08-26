# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import CustomUser
#
# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     list_display = ['username', 'phone_number', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
#     list_filter = ['is_staff', 'is_active', 'is_superuser', 'date_joined']
#     search_fields = ['username', 'phone_number', 'email', 'first_name', 'last_name']
#     ordering = ['username']
#
#     fieldsets = (
#         (None, {'fields': ('phone_number', 'password')}),
#         ('Личная информация', {'fields': ('username', 'first_name', 'last_name', 'email')}),
#         ('Разрешения', {
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
#         }),
#         ('Важные даты', {'fields': ('last_login', 'date_joined')}),
#     )
#
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('phone_number', 'username', 'password1', 'password2'),
#         }),
#     )
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined', 'last_login']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']

    # Добавляем новые поля в форму редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone_number', 'birth_date')
        }),
    )

    # Добавляем поля в форму создания пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'birth_date')
        }),
    )

    # Дополнительные действия
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} пользователей активированы.')

    make_active.short_description = "Активировать выбранных пользователей"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} пользователей деактивированы.')

    make_inactive.short_description = "Деактивировать выбранных пользователей"