from django.contrib import admin
from django.utils.html import format_html
from .models import *


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_main', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock', 'is_active', 'is_featured']
    inlines = [ProductImageInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'category', 'sku')
        }),
        ('Описание', {
            'fields': ('short_description', 'description')
        }),
        ('Цены и остатки', {
            'fields': ('price', 'old_price', 'stock')
        }),
        ('Характеристики', {
            'fields': ('weight', 'dimensions', 'rating')
        }),
        ('Настройки', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'total_price', 'updated_at']
    readonly_fields = ['total_price', 'total_items']
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'is_paid', 'created_at', 'get_items_count']
    list_filter = ['status', 'is_paid', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'phone', 'email']
    list_editable = ['status', 'is_paid']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    actions = ['cancel_orders', 'restore_orders']

    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_city', 'delivery_postal_code')
        }),
        ('Контакты', {
            'fields': ('phone', 'email')
        }),
        ('Оплата', {
            'fields': ('subtotal', 'delivery_cost', 'total', 'payment_method', 'is_paid')
        }),
        ('Дополнительно', {
            'fields': ('notes',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_items_count(self, obj):
        return obj.items.count()

    get_items_count.short_description = 'Кол-во товаров'

    def cancel_orders(self, request, queryset):
        """Отменить выбранные заказы"""
        count = 0
        for order in queryset.exclude(status='cancelled'):
            order.status = 'cancelled'
            order.save()  # Сигнал автоматически вернет товары на склад
            count += 1

        self.message_user(
            request,
            f'Отменено заказов: {count}. Товары возвращены на склад.'
        )

    cancel_orders.short_description = 'Отменить выбранные заказы'

    def restore_orders(self, request, queryset):
        """Восстановить отмененные заказы"""
        count = 0
        for order in queryset.filter(status='cancelled'):
            order.status = 'pending'
            order.save()  # Сигнал автоматически зарезервирует товары
            count += 1

        self.message_user(
            request,
            f'Восстановлено заказов: {count}. Товары зарезервированы со склада.'
        )

    restore_orders.short_description = 'Восстановить отмененные заказы'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Убеждаемся, что поля имеют правильные значения по умолчанию
        if not obj:  # Только для новых объектов
            form.base_fields['subtotal'].initial = 0
            form.base_fields['delivery_cost'].initial = 0
            form.base_fields['total'].initial = 0
        return form


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['user__username', 'product__name', 'title', 'comment']
    list_editable = ['is_verified']
    readonly_fields = ['created_at']