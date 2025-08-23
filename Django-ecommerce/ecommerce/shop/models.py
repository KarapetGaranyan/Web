from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='categories/', blank=True, verbose_name='Изображение')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               related_name='children', verbose_name='Родительская категория')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL')
    description = models.TextField(verbose_name='Описание')
    short_description = models.CharField(max_length=500, blank=True, verbose_name='Краткое описание')
    category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                 related_name='products', verbose_name='Категория')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    verbose_name='Старая цена')
    stock = models.PositiveIntegerField(default=0, verbose_name='Остаток')
    sku = models.CharField(max_length=100, unique=True, verbose_name='Артикул')
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                 verbose_name='Вес (кг)')
    dimensions = models.CharField(max_length=100, blank=True, verbose_name='Размеры')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0,
                                 validators=[MinValueValidator(0), MaxValueValidator(5)],
                                 verbose_name='Рейтинг')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def discount_percentage(self):
        if self.old_price and self.old_price > self.price:
            return round(((self.old_price - self.price) / self.old_price) * 100)
        return 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images', verbose_name='Товар')
    image = models.ImageField(upload_to='products/', verbose_name='Изображение')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='Alt текст')
    is_main = models.BooleanField(default=False, verbose_name='Главное изображение')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} - {self.order}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Оптимизация изображения
        if self.image:
            img = Image.open(self.image.path)
            if img.height > 800 or img.width > 800:
                output_size = (800, 800)
                img.thumbnail(output_size)
                img.save(self.image.path)


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f"Корзина {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE,
                             related_name='items', verbose_name='Корзина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлен')

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтвержден'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    PAYMENT_CHOICES = [
        ('cash', 'Наличными'),
        ('card', 'Картой'),
        ('online', 'Онлайн'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='orders', verbose_name='Пользователь', db_index=True)
    order_number = models.CharField(max_length=20, unique=True, verbose_name='Номер заказа')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='pending', verbose_name='Статус', db_index=True)

    # Адрес доставки
    delivery_address = models.TextField(verbose_name='Адрес доставки')
    delivery_city = models.CharField(max_length=100, verbose_name='Город')
    delivery_postal_code = models.CharField(max_length=20, verbose_name='Почтовый индекс')

    # Контактная информация
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(verbose_name='Email')

    # Финансовая информация
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма товаров')
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2,
                                        default=0, verbose_name='Стоимость доставки')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая сумма', db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES,
                                      default='cash', verbose_name='Способ оплаты')
    is_paid = models.BooleanField(default=False, verbose_name='Оплачен', db_index=True)

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    # Дополнительная информация
    notes = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        # Составные индексы для админки и отчетов
        indexes = [
            models.Index(fields=['user', 'status'], name='order_user_status'),
            models.Index(fields=['status', 'created_at'], name='order_status_date'),
            models.Index(fields=['user', 'created_at'], name='order_user_date'),
            models.Index(fields=['is_paid', 'status'], name='order_paid_status'),
        ]

    def __str__(self):
        return f"Заказ #{self.order_number}"

    def save(self, *args, **kwargs):
        # Проверяем, изменился ли статус заказа
        if self.pk:  # Если заказ уже существует
            old_order = Order.objects.get(pk=self.pk)
            old_status = old_order.status
            new_status = self.status

            # Если заказ отменяется, возвращаем товары на склад
            if old_status != 'cancelled' and new_status == 'cancelled':
                self.cancel_order()

            # Если заказ восстанавливается из отмененного, снова списываем товары
            elif old_status == 'cancelled' and new_status != 'cancelled':
                self.restore_order()

        if not self.order_number:
            import uuid
            self.order_number = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def cancel_order(self):
        """Отменить заказ и вернуть товары на склад"""
        for item in self.items.all():
            # Возвращаем количество товара обратно на склад
            item.product.stock += item.quantity
            item.product.save()
            print(f"Returned {item.quantity} units of {item.product.name} to stock")

    def restore_order(self):
        """Восстановить заказ и списать товары со склада"""
        for item in self.items.all():
            # Проверяем, достаточно ли товара на складе
            if item.product.stock >= item.quantity:
                item.product.stock -= item.quantity
                item.product.save()
                print(f"Reserved {item.quantity} units of {item.product.name}")
            else:
                # Если товара недостаточно, устанавливаем максимально возможное количество
                available = item.product.stock
                item.product.stock = 0
                item.quantity = available
                item.save()
                item.product.save()
                print(f"Partially restored: only {available} units of {item.product.name} available")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='reviews', verbose_name='Товар')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
                                         verbose_name='Оценка')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    comment = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    is_verified = models.BooleanField(default=False, verbose_name='Подтвержден')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}/5)"