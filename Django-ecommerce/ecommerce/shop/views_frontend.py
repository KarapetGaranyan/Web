from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import *
from .filters import ProductFilter

from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator


def home(request):
    """Главная страница (С КЭШИРОВАНИЕМ)"""
    # Попытаемся получить данные из кэша
    cache_key = 'home_page_data'
    cached_data = cache.get(cache_key)

    if cached_data is None:
        # Если данных в кэше нет, получаем их из БД
        featured_products = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related('category').prefetch_related('images')[:8]

        categories = Category.objects.filter(
            is_active=True,
            parent=None
        )[:6]

        cached_data = {
            'featured_products': list(featured_products),
            'categories': list(categories)
        }

        # Кэшируем на 15 минут
        cache.set(cache_key, cached_data, 60 * 15)

    context = {
        'featured_products': cached_data['featured_products'],
        'categories': cached_data['categories'],
    }
    return render(request, 'shop/home.html', context)


def product_list(request):
    """Список товаров с фильтрацией (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)"""
    # Оптимизируем запрос с select_related для категорий и prefetch_related для изображений
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
    categories = Category.objects.filter(is_active=True)

    # Применяем фильтры
    product_filter = ProductFilter(request.GET, queryset=products)
    products = product_filter.qs

    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )

    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['name', '-name', 'price', '-price', 'created_at', '-created_at', 'rating', '-rating']
    if sort_by in valid_sorts:
        products = products.order_by(sort_by)

    # Пагинация
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'filter': product_filter,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, slug):
    """Детальная страница товара (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)"""
    # Оптимизируем запрос с select_related и prefetch_related
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'reviews__user'),
        slug=slug,
        is_active=True
    )

    # Получаем отзывы с пользователями одним запросом
    reviews = product.reviews.filter(is_verified=True).select_related('user').order_by('-created_at')

    # Похожие товары с оптимизацией
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]

    # Средний рейтинг
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    context = {
        'product': product,
        'reviews': reviews,
        'related_products': related_products,
        'avg_rating': round(avg_rating, 1),
        'reviews_count': reviews.count(),
    }
    return render(request, 'shop/product_detail.html', context)


def category_detail(request, slug):
    """Страница категории"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(category=category, is_active=True)

    # Подкатегории
    subcategories = category.children.filter(is_active=True)

    # Пагинация
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj,
        'subcategories': subcategories,
    }
    return render(request, 'shop/category_detail.html', context)


@login_required
def cart_view(request):
    """Страница корзины (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)"""
    # Оптимизируем запрос корзины с товарами
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Если корзина существует, получаем товары с оптимизацией
    if not created:
        cart = Cart.objects.prefetch_related(
            'items__product__category',
            'items__product__images'
        ).get(user=request.user)

    context = {
        'cart': cart,
    }
    return render(request, 'shop/cart.html', context)


@login_required
@require_POST
@csrf_exempt
def add_to_cart(request):
    """Добавить товар в корзину (AJAX)"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, is_active=True)

        if product.stock < quantity:
            return JsonResponse({'success': False, 'message': 'Недостаточно товара в наличии'})

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock:
                return JsonResponse({'success': False, 'message': 'Недостаточно товара в наличии'})
            cart_item.save()

        return JsonResponse({
            'success': True,
            'message': 'Товар добавлен в корзину',
            'cart_total': cart.total_items
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def update_cart_item(request, item_id):
    """Обновить количество товара в корзине (AJAX)"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))

        if quantity <= 0:
            cart_item.delete()
            return JsonResponse({'success': True, 'message': 'Товар удален из корзины'})

        if quantity > cart_item.product.stock:
            return JsonResponse({'success': False, 'message': 'Недостаточно товара в наличии'})

        cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({
            'success': True,
            'message': 'Количество обновлено',
            'total_price': float(cart_item.total_price),
            'cart_total': float(cart_item.cart.total_price)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
@csrf_exempt
def remove_from_cart(request, item_id):
    """Удалить товар из корзины (AJAX)"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()

        return JsonResponse({
            'success': True,
            'message': f'Товар "{product_name}" удален из корзины'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@login_required
def checkout(request):
    """Страница оформления заказа"""
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        messages.error(request, 'Ваша корзина пуста')
        return redirect('cart')

    # Проверяем наличие товаров
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(request, f'Товар "{item.product.name}" недоступен в нужном количестве')
            return redirect('cart')

    delivery_cost = 300  # Фиксированная стоимость доставки
    total = cart.total_price + delivery_cost

    if request.method == 'POST':
        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            delivery_address=request.POST.get('delivery_address'),
            delivery_city=request.POST.get('delivery_city'),
            delivery_postal_code=request.POST.get('delivery_postal_code'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            payment_method=request.POST.get('payment_method', 'cash'),
            notes=request.POST.get('notes', ''),
            subtotal=cart.total_price,
            delivery_cost=delivery_cost,
            total=total
        )

        # Создаем позиции заказа
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            # Уменьшаем остаток
            item.product.stock -= item.quantity
            item.product.save()

        # Очищаем корзину
        cart.items.all().delete()

        messages.success(request, f'Заказ #{order.order_number} успешно создан!')
        return redirect('order_detail', order_id=order.id)

    context = {
        'cart': cart,
        'delivery_cost': delivery_cost,
        'total': total,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def order_list(request):
    """Список заказов пользователя"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'shop/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """Детали заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'shop/order_detail.html', context)


# Удаляем эту функцию, так как она теперь в accounts/views.py


def search(request):
    """Поиск товаров"""
    query = request.GET.get('q', '')
    products = Product.objects.none()

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query),
            is_active=True
        )

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'total_results': products.count(),
    }
    return render(request, 'shop/search_results.html', context)


@login_required
@require_POST
def add_review(request, product_id):
    """Добавить отзыв к товару"""
    product = get_object_or_404(Product, id=product_id, is_active=True)

    # Проверяем, не оставлял ли пользователь уже отзыв
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, 'Вы уже оставили отзыв к этому товару')
        return redirect('product_detail', slug=product.slug)

    rating = int(request.POST.get('rating', 5))
    title = request.POST.get('title', '')
    comment = request.POST.get('comment', '')

    Review.objects.create(
        user=request.user,
        product=product,
        rating=rating,
        title=title,
        comment=comment
    )

    messages.success(request, 'Отзыв добавлен и ожидает модерации')
    return redirect('product_detail', slug=product.slug)