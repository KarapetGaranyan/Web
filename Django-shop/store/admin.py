from django.contrib import admin
from .models import Category, Product, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'available', 'created']
    list_filter = ['available', 'created', 'category']
    list_editable = ['price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created'

    # Добавляем действие для пополнения склада
    actions = ['replenish_stock', 'make_available', 'make_unavailable']

    def replenish_stock(self, request, queryset):
        """Пополнить склад (добавить 10 единиц к каждому товару)"""
        updated = 0
        for product in queryset:
            product.stock += 10
            product.available = True  # Делаем товар доступным
            product.save()
            updated += 1

        self.message_user(request, f'Склад пополнен для {updated} товаров (+10 единиц к каждому)')

    replenish_stock.short_description = "Пополнить склад (+10 к каждому)"

    def make_available(self, request, queryset):
        queryset.update(available=True)

    make_available.short_description = "Сделать доступными"

    def make_unavailable(self, request, queryset):
        queryset.update(available=False)

    make_unavailable.short_description = "Сделать недоступными"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price', 'get_total']

    def get_total(self, obj):
        if obj.price and obj.quantity:
            return f"{obj.price * obj.quantity} ₽"
        return "0 ₽"

    get_total.short_description = "Сумма"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_customer_name', 'get_customer_contact', 'total_amount', 'status', 'created']
    list_filter = ['status', 'created']
    search_fields = ['customer_name', 'customer_email', 'customer_phone', 'user__username']
    readonly_fields = ['created', 'updated', 'total_amount']
    inlines = [OrderItemInline]
    date_hierarchy = 'created'

    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    def get_customer_name(self, obj):
        if obj.user:
            return f"{obj.user.username} (зарегистрирован)"
        return obj.customer_name or "Без имени"

    get_customer_name.short_description = "Клиент"

    def get_customer_contact(self, obj):
        if obj.user:
            return obj.user.email or "Нет email"
        return obj.customer_email or "Нет email"

    get_customer_contact.short_description = "Контакт"

    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')

    mark_as_paid.short_description = "Отметить как оплаченные"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')

    mark_as_shipped.short_description = "Отметить как отправленные"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')

    mark_as_delivered.short_description = "Отметить как доставленные"

    def mark_as_cancelled(self, request, queryset):
        """Отменить заказ (товары автоматически вернутся на склад через сигнал)"""
        updated = 0
        for order in queryset:
            if order.status != 'cancelled':
                order.status = 'cancelled'
                order.save()  # Сигнал автоматически вернет товары на склад
                updated += 1

        self.message_user(request, f'{updated} заказов отменено, товары возвращены на склад')

    mark_as_cancelled.short_description = "Отменить заказы (вернуть товары на склад)"