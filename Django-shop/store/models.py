from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    slug = models.SlugField(unique=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    name = models.CharField(max_length=200, verbose_name="Название")
    slug = models.SlugField(unique=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to='products/', default='test.png', verbose_name="Изображение")
    stock = models.PositiveIntegerField(default=0, verbose_name="Остаток")
    available = models.BooleanField(default=True, verbose_name="Доступен")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    # Связь с пользователем (может быть null для гостевых заказов)
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, null=True, blank=True,
                             verbose_name="Пользователь")

    # Данные клиента (заполняются для гостевых заказов)
    customer_name = models.CharField(max_length=200, verbose_name="Имя клиента", blank=True)
    customer_email = models.EmailField(verbose_name="Email клиента", blank=True)
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон клиента", blank=True)

    address = models.TextField(verbose_name="Адрес доставки")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created']

    def __str__(self):
        if self.user:
            return f"Заказ #{self.id} - {self.user.username}"
        else:
            return f"Заказ #{self.id} - {self.customer_name}"

    def return_products_to_stock(self):
        """Возвращает товары из заказа обратно на склад"""
        for item in self.items.all():
            product = item.product
            product.stock += item.quantity
            # Делаем товар доступным если он был недоступен
            if not product.available and product.stock > 0:
                product.available = True
            product.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


# СИГНАЛЫ ДЛЯ АВТОМАТИЧЕСКОГО УПРАВЛЕНИЯ ОСТАТКАМИ

@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """
    Обрабатываем изменение статуса заказа.
    Если заказ отменяется - возвращаем товары на склад.
    """
    if instance.pk:  # Проверяем, что это обновление существующего заказа
        try:
            # Получаем старую версию заказа из базы данных
            old_order = Order.objects.get(pk=instance.pk)

            # Если статус изменился на "отменен"
            if old_order.status != 'cancelled' and instance.status == 'cancelled':
                print(f"Заказ #{instance.id} отменен. Возвращаем товары на склад.")
                instance.return_products_to_stock()

            # Если заказ восстанавливается из отмененного состояния
            elif old_order.status == 'cancelled' and instance.status != 'cancelled':
                print(f"Заказ #{instance.id} восстановлен из отмененного. Списываем товары со склада.")
                # Списываем товары обратно со склада
                for item in instance.items.all():
                    product = item.product
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        if product.stock == 0:
                            product.available = False
                        product.save()
                    else:
                        # Если товара недостаточно, не даем восстановить заказ
                        raise ValueError(f"Недостаточно товара '{product.name}' на складе для восстановления заказа")

        except Order.DoesNotExist:
            # Это новый заказ, ничего не делаем
            pass
        except Exception as e:
            print(f"Ошибка при обработке изменения статуса заказа: {e}")
            # В случае ошибки можно либо проигнорировать, либо вызвать исключение
            # raise e