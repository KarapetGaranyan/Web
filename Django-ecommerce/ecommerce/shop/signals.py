# shop/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Order


@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """Обрабатываем изменение статуса заказа"""
    if instance.pk:  # Если заказ уже существует
        try:
            old_order = Order.objects.get(pk=instance.pk)
            old_status = old_order.status
            new_status = instance.status

            # Логируем изменение статуса
            if old_status != new_status:
                print(f"Order #{instance.order_number} status changed: {old_status} -> {new_status}")

                # Если заказ отменяется, возвращаем товары на склад
                if old_status != 'cancelled' and new_status == 'cancelled':
                    return_items_to_stock(instance)

                # Если заказ восстанавливается из отмененного, снова списываем товары
                elif old_status == 'cancelled' and new_status != 'cancelled':
                    reserve_items_from_stock(instance)

        except Order.DoesNotExist:
            pass


def return_items_to_stock(order):
    """Возвращаем товары на склад при отмене заказа"""
    for item in order.items.all():
        # Возвращаем количество товара обратно на склад
        item.product.stock += item.quantity
        item.product.save()
        print(f"Returned {item.quantity} units of '{item.product.name}' to stock (new stock: {item.product.stock})")


def reserve_items_from_stock(order):
    """Резервируем товары со склада при восстановлении заказа"""
    for item in order.items.all():
        # Проверяем, достаточно ли товара на складе
        if item.product.stock >= item.quantity:
            item.product.stock -= item.quantity
            item.product.save()
            print(f"Reserved {item.quantity} units of '{item.product.name}' (remaining stock: {item.product.stock})")
        else:
            # Если товара недостаточно, отмечаем проблему
            available = item.product.stock
            print(
                f"WARNING: Not enough stock for '{item.product.name}'. Requested: {item.quantity}, Available: {available}")

            # Можно либо частично зарезервировать, либо оставить как есть
            # Здесь оставляем как есть и уведомляем администратора