from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Category, Product, Order, OrderItem
import json

# Добавьте эти импорты в начало views.py
from django.conf import settings
from yookassa import Configuration, Payment
import uuid
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import json

# Настройка ЮKassa
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(request, 'store/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products
    })


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    categories = Category.objects.all()
    return render(request, 'store/product_detail.html', {
        'product': product,
        'categories': categories
    })


def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, available=True)

        cart = request.session.get('cart', {})

        # Проверяем доступность товара на складе
        current_in_cart = cart.get(str(product_id), {}).get('quantity', 0)
        total_requested = current_in_cart + quantity

        if total_requested > product.stock:
            return JsonResponse({
                'success': False,
                'message': f'Недостаточно товара на складе. Доступно: {product.stock} шт., в корзине: {current_in_cart} шт.',
                'cart_count': sum(item['quantity'] for item in cart.values())
            })

        # Добавляем товар в корзину
        if str(product_id) in cart:
            cart[str(product_id)]['quantity'] += quantity
        else:
            cart[str(product_id)] = {
                'name': product.name,
                'price': str(product.price),
                'quantity': quantity,
                'image': product.image.url if product.image else '/static/images/no-image.png'
            }

        request.session['cart'] = cart
        request.session.modified = True

        # Вычисляем общее количество товаров в корзине
        cart_count = sum(item['quantity'] for item in cart.values())

        return JsonResponse({
            'success': True,
            'message': f'{product.name} добавлен в корзину ({quantity} шт.)',
            'cart_count': cart_count,
            'product_name': product.name,
            'quantity': quantity,
            'total_price': float(product.price) * quantity
        })

    return JsonResponse({'success': False, 'message': 'Неверный запрос'})


def update_cart_quantity(request):
    """Обновление количества товара в корзине через POST форму"""
    if request.method == 'POST':
        product_id = str(request.POST.get('product_id'))
        new_quantity = int(request.POST.get('quantity', 1))

        if new_quantity < 1:
            messages.error(request, 'Количество должно быть больше 0')
            return redirect('store:cart_detail')

        cart = request.session.get('cart', {})

        if product_id in cart:
            # Проверяем наличие товара на складе
            product = get_object_or_404(Product, id=product_id)
            if new_quantity > product.stock:
                messages.error(request, f'Недостаточно товара на складе. Доступно: {product.stock} шт.')
                return redirect('store:cart_detail')

            cart[product_id]['quantity'] = new_quantity
            request.session['cart'] = cart
            request.session.modified = True

            messages.success(request, 'Количество товара обновлено')
        else:
            messages.error(request, 'Товар не найден в корзине')

    return redirect('store:cart_detail')


def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    categories = Category.objects.all()

    for product_id, item in cart.items():
        product = Product.objects.get(id=product_id)
        item_total = product.price * item['quantity']
        cart_items.append({
            'product': product,
            'quantity': item['quantity'],
            'total': item_total
        })
        total += item_total

    return render(request, 'store/cart_detail.html', {
        'cart_items': cart_items,
        'total': total,
        'categories': categories
    })


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Товар удален из корзины')

    return redirect('store:cart_detail')


def order_create(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Ваша корзина пуста')
        return redirect('store:product_list')

    if request.method == 'POST':
        # Создаем заказ
        order_data = {
            'address': request.POST['address'],
            'total_amount': 0
        }

        # Если пользователь авторизован, связываем заказ с ним
        if request.user.is_authenticated:
            order_data['user'] = request.user
        else:
            # Для гостевых заказов заполняем данные клиента
            order_data['customer_name'] = request.POST['customer_name']
            order_data['customer_email'] = request.POST['customer_email']
            order_data['customer_phone'] = request.POST['customer_phone']

        order = Order.objects.create(**order_data)

        total_amount = 0

        # Создаем позиции заказа и уменьшаем остатки на складе
        for product_id, item in cart.items():
            product = Product.objects.get(id=product_id)
            price = product.price
            quantity = item['quantity']
            item_total = price * quantity

            # Проверяем достаточно ли товара на складе
            if quantity > product.stock:
                # Если недостаточно товара, удаляем заказ и показываем ошибку
                order.delete()
                messages.error(request,
                               f'Недостаточно товара "{product.name}" на складе. Доступно: {product.stock} шт.')
                return redirect('store:cart_detail')

            # Создаем позицию заказа
            OrderItem.objects.create(
                order=order,
                product=product,
                price=price,
                quantity=quantity
            )

            # УМЕНЬШАЕМ ОСТАТОК НА СКЛАДЕ
            product.stock -= quantity
            if product.stock == 0:
                product.available = False  # Делаем товар недоступным если закончился
            product.save()

            total_amount += item_total

        # Обновляем общую сумму заказа
        order.total_amount = total_amount
        order.save()

        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True

        # Для гостевых заказов сохраняем информацию в сессии
        if not request.user.is_authenticated:
            guest_order_key = f'guest_order_{order.id}'
            request.session[guest_order_key] = True
            request.session.modified = True

        messages.success(request, f'Заказ #{order.id} успешно создан! Товары списаны со склада.')
        return redirect('store:order_success', order_id=order.id)

    cart_items = []
    total = 0
    categories = Category.objects.all()

    for product_id, item in cart.items():
        product = Product.objects.get(id=product_id)
        item_total = product.price * item['quantity']
        cart_items.append({
            'product': product,
            'quantity': item['quantity'],
            'total': item_total
        })
        total += item_total

    return render(request, 'store/order_create.html', {
        'cart_items': cart_items,
        'total': total,
        'categories': categories
    })


def cancel_order(request, order_id):
    """Отмена заказа пользователем"""
    try:
        if request.user.is_authenticated:
            order = get_object_or_404(Order, id=order_id, user=request.user)
        else:
            # Для гостевых заказов проверяем через сессию
            guest_order_key = f'guest_order_{order_id}'
            if guest_order_key not in request.session:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')
            order = get_object_or_404(Order, id=order_id, user=None)

        # НОВАЯ ЛОГИКА: проверяем, можно ли отменить заказ
        if order.status in ['shipped', 'delivered', 'cancelled']:
            if order.status == 'shipped':
                messages.error(request, 'Заказ уже отправлен и не может быть отменен.')
            elif order.status == 'delivered':
                messages.error(request, 'Заказ уже доставлен и не может быть отменен.')
            elif order.status == 'cancelled':
                messages.info(request, 'Заказ уже отменен.')

            return redirect('store:order_success', order_id=order_id)

        if request.method == 'POST':
            # Отменяем заказ (сигнал автоматически вернет товары на склад)
            old_status = order.status
            order.status = 'cancelled'
            order.save()

            messages.success(request,
                             f'Заказ #{order.id} успешно отменен. Товары возвращены на склад.')

            # Если пользователь авторизован, перенаправляем в личный кабинет
            if request.user.is_authenticated:
                return redirect('accounts:profile')
            else:
                return redirect('store:order_success', order_id=order_id)

    except Exception as e:
        messages.error(request, 'Ошибка при отмене заказа.')
        return redirect('store:product_list')

    # Показываем страницу подтверждения отмены
    categories = Category.objects.all()
    return render(request, 'store/cancel_order.html', {
        'order': order,
        'categories': categories
    })


def order_success(request, order_id):
    # Получаем заказ с проверкой прав доступа
    try:
        if request.user.is_authenticated:
            # Для авторизованных пользователей - только их заказы
            order = get_object_or_404(Order, id=order_id, user=request.user)
        else:
            # Для гостевых заказов - проверяем через сессию
            guest_order_key = f'guest_order_{order_id}'
            if guest_order_key not in request.session:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')

            order = get_object_or_404(Order, id=order_id)
            # Проверяем, что это действительно гостевой заказ (без пользователя)
            if order.user is not None:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')
    except:
        messages.error(request, 'Заказ не найден.')
        return redirect('store:product_list')

    categories = Category.objects.all()
    return render(request, 'store/order_success.html', {
        'order': order,
        'categories': categories
    })


def create_payment(request, order_id):
    """Создание платежа через YooKassa"""
    try:
        if request.user.is_authenticated:
            order = get_object_or_404(Order, id=order_id, user=request.user)
        else:
            guest_order_key = f'guest_order_{order_id}'
            if guest_order_key not in request.session:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')
            order = get_object_or_404(Order, id=order_id, user=None)

        # Проверяем, что заказ можно оплатить
        if order.status != 'pending':
            messages.error(request, 'Этот заказ нельзя оплатить.')
            return redirect('store:order_success', order_id=order_id)

        # Проверяем, используются ли демо-ключи
        using_demo_keys = (settings.YOOKASSA_SHOP_ID == "54401" and
                           "test_" in settings.YOOKASSA_SECRET_KEY)

        if using_demo_keys:
            # ДЕМО-РЕЖИМ: имитируем создание платежа
            import uuid
            import time

            demo_payment_id = f"demo_{uuid.uuid4().hex[:8]}"

            # Сохраняем демо-платеж в сессии
            request.session[f'demo_payment_{order.id}'] = {
                'payment_id': demo_payment_id,
                'order_id': order.id,
                'amount': str(order.total_amount),
                'created_at': time.time()
            }
            request.session.modified = True

            messages.info(request, f'Демо-платеж создан (ID: {demo_payment_id}). Переходим к имитации оплаты...')

            # Перенаправляем на страницу "оплаты"
            return redirect('store:demo_payment_page', order_id=order.id)

        else:
            # РЕАЛЬНЫЙ РЕЖИМ: создаем настоящий платеж YooKassa
            try:
                from yookassa import Configuration, Payment
                import uuid

                Configuration.account_id = settings.YOOKASSA_SHOP_ID
                Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

                payment = Payment.create({
                    "amount": {
                        "value": str(order.total_amount),
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": request.build_absolute_uri(
                            reverse('store:payment_success', args=[order.id])
                        )
                    },
                    "capture": True,
                    "description": f"Оплата заказа #{order.id}",
                    "test": True,  # Тестовый режим
                    "metadata": {
                        "order_id": str(order.id)
                    }
                }, str(uuid.uuid4()))

                # Сохраняем ID платежа в сессии
                request.session[f'payment_{order.id}'] = payment.id
                request.session.modified = True

                # Перенаправляем на страницу оплаты YooKassa
                return redirect(payment.confirmation.confirmation_url)

            except Exception as e:
                messages.error(request, f'Ошибка при создании платежа: {str(e)}')
                return redirect('store:order_success', order_id=order_id)

    except Exception as e:
        messages.error(request, 'Ошибка при обработке платежа.')
        return redirect('store:product_list')


def demo_payment_page(request, order_id):
    """Демо-страница имитации оплаты"""
    try:
        if request.user.is_authenticated:
            order = get_object_or_404(Order, id=order_id, user=request.user)
        else:
            guest_order_key = f'guest_order_{order_id}'
            if guest_order_key not in request.session:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')
            order = get_object_or_404(Order, id=order_id, user=None)

        # Получаем демо-платеж из сессии
        demo_payment = request.session.get(f'demo_payment_{order.id}')
        if not demo_payment:
            messages.error(request, 'Платеж не найден.')
            return redirect('store:order_success', order_id=order_id)

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'success':
                # Имитируем успешную оплату
                order.status = 'paid'
                order.save()

                # Удаляем демо-платеж из сессии
                del request.session[f'demo_payment_{order.id}']
                request.session.modified = True

                messages.success(request, f'Демо-оплата успешна! Заказ #{order.id} оплачен.')
                return redirect('store:order_success', order_id=order.id)

            elif action == 'fail':
                # Имитируем неудачную оплату
                messages.error(request, 'Демо-оплата отклонена. Попробуйте еще раз.')
                return redirect('store:order_success', order_id=order.id)

        categories = Category.objects.all()
        context = {
            'order': order,
            'demo_payment': demo_payment,
            'categories': categories
        }
        return render(request, 'store/demo_payment.html', context)

    except Exception as e:
        messages.error(request, 'Ошибка при обработке платежа.')
        return redirect('store:product_list')


def payment_success(request, order_id):
    """Обработка успешной оплаты"""
    try:
        if request.user.is_authenticated:
            order = get_object_or_404(Order, id=order_id, user=request.user)
        else:
            guest_order_key = f'guest_order_{order_id}'
            if guest_order_key not in request.session:
                messages.error(request, 'Доступ к заказу запрещен.')
                return redirect('store:product_list')
            order = get_object_or_404(Order, id=order_id, user=None)

        # Проверяем демо-режим
        using_demo_keys = (settings.YOOKASSA_SHOP_ID == "54401" and
                           "test_" in settings.YOOKASSA_SECRET_KEY)

        if using_demo_keys:
            # В демо-режиме просто подтверждаем "оплату"
            order.status = 'paid'
            order.save()
            messages.success(request, 'Демо-платеж завершен! Заказ оплачен.')
        else:
            # Реальный режим - проверяем статус платежа в YooKassa
            payment_id = request.session.get(f'payment_{order.id}')

            if payment_id:
                from yookassa import Payment
                payment = Payment.find_one(payment_id)

                if payment.status == 'succeeded':
                    order.status = 'paid'
                    order.save()

                    # Удаляем ID платежа из сессии
                    del request.session[f'payment_{order.id}']
                    request.session.modified = True

                    messages.success(request, 'Платеж успешно выполнен! Заказ оплачен.')
                elif payment.status == 'pending':
                    messages.info(request, 'Платеж обрабатывается. Пожалуйста, подождите.')
                else:
                    messages.error(request, 'Платеж не выполнен. Попробуйте еще раз.')

    except Exception as e:
        messages.error(request, f'Ошибка при проверке платежа: {str(e)}')

    return redirect('store:order_success', order_id=order_id)