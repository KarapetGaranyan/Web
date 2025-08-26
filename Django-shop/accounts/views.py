# from django.shortcuts import render, redirect
# from django.contrib.auth import login, logout, authenticate
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.contrib.auth.forms import AuthenticationForm
# from .forms import CustomUserCreationForm, CustomAuthenticationForm
# from store.models import Order
#
# def register(request):
#     if request.user.is_authenticated:
#         return redirect('store:product_list')
#
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             login(request, user)
#             messages.success(request, f'Аккаунт успешно создан! Добро пожаловать, {user.username}!')
#             return redirect('store:product_list')
#         else:
#             messages.error(request, 'Ошибка при создании аккаунта. Проверьте введенные данные.')
#     else:
#         form = CustomUserCreationForm()
#
#     return render(request, 'accounts/register.html', {'form': form})
#
# def user_login(request):
#     if request.user.is_authenticated:
#         return redirect('store:product_list')
#
#     if request.method == 'POST':
#         form = CustomAuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             phone_number = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(request, phone_number=phone_number, password=password)
#             if user is not None:
#                 login(request, user)
#                 messages.success(request, f'Добро пожаловать, {user.username}!')
#                 return redirect('store:product_list')
#             else:
#                 messages.error(request, 'Неверный номер телефона или пароль.')
#         else:
#             messages.error(request, 'Неверный номер телефона или пароль.')
#     else:
#         form = CustomAuthenticationForm()
#
#     return render(request, 'accounts/login.html', {'form': form})
#
# @login_required
# def user_logout(request):
#     logout(request)
#     messages.success(request, 'Вы успешно вышли из аккаунта.')
#     return redirect('store:product_list')
#
# @login_required
# def profile(request):
#     # Получаем заказы пользователя
#     orders = Order.objects.filter(user=request.user).order_by('-created')
#
#     return render(request, 'accounts/profile.html', {
#         'orders': orders
#     })
#
# @login_required
# def order_detail(request, order_id):
#     # Получаем заказ только для текущего пользователя
#     try:
#         order = Order.objects.get(id=order_id, user=request.user)
#     except Order.DoesNotExist:
#         messages.error(request, 'Заказ не найден.')
#         return redirect('accounts:profile')
#
#     return render(request, 'accounts/order_detail.html', {
#         'order': order
#     })
# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from .forms import CustomUserCreationForm, UserProfileForm
from .models import CustomUser
from store.models import Order, Category


def register_view(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт успешно создан для {username}!')
            # Автоматический вход после регистрации
            login(request, user)
            return redirect('store:product_list')
    else:
        form = CustomUserCreationForm()

    categories = Category.objects.all()
    return render(request, 'accounts/register.html', {
        'form': form,
        'categories': categories
    })


def login_view(request):
    """Вход пользователя"""
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.username}!')
                # Перенаправление на страницу, с которой пришел пользователь
                next_url = request.GET.get('next', 'store:product_list')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()

    categories = Category.objects.all()
    return render(request, 'accounts/login.html', {
        'form': form,
        'categories': categories
    })


def logout_view(request):
    """Выход пользователя"""
    username = request.user.username if request.user.is_authenticated else None
    logout(request)
    if username:
        messages.success(request, f'До свидания, {username}!')
    return redirect('store:product_list')


@login_required
def profile_view(request):
    """Профиль пользователя с заказами и статистикой"""

    # Получаем все заказы пользователя
    user_orders = Order.objects.filter(user=request.user).order_by('-created')

    # Статистика заказов
    total_orders = user_orders.count()
    total_spent = sum(order.total_amount for order in user_orders if order.status != 'cancelled')

    orders_by_status = {
        'pending': user_orders.filter(status='pending').count(),
        'paid': user_orders.filter(status='paid').count(),
        'shipped': user_orders.filter(status='shipped').count(),
        'delivered': user_orders.filter(status='delivered').count(),
        'cancelled': user_orders.filter(status='cancelled').count(),
    }

    # Пагинация заказов
    paginator = Paginator(user_orders, 10)  # 10 заказов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Обновление профиля
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    categories = Category.objects.all()
    context = {
        'form': form,
        'user_orders': page_obj,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'orders_by_status': orders_by_status,
        'categories': categories,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def order_detail_view(request, order_id):
    """Детальный просмотр заказа пользователем"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Определяем, можно ли отменить заказ
    can_cancel = order.status in ['pending', 'paid']  # Нельзя отменить отправленные и доставленные

    categories = Category.objects.all()
    context = {
        'order': order,
        'can_cancel': can_cancel,
        'categories': categories,
    }
    return render(request, 'accounts/order_detail.html', context)