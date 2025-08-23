from django.urls import path
from . import views_frontend

urlpatterns = [
    # Главная страница
    path('', views_frontend.home, name='home'),

    # Товары
    path('products/', views_frontend.product_list, name='product_list'),
    path('product/<slug:slug>/', views_frontend.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views_frontend.category_detail, name='category_detail'),

    # Поиск
    path('search/', views_frontend.search, name='search'),

    # Корзина
    path('cart/', views_frontend.cart_view, name='cart'),
    path('cart/add/', views_frontend.add_to_cart, name='add_to_cart_ajax'),
    path('cart/update/<int:item_id>/', views_frontend.update_cart_item, name='update_cart_item_ajax'),
    path('cart/remove/<int:item_id>/', views_frontend.remove_from_cart, name='remove_from_cart_ajax'),

    # Заказы
    path('checkout/', views_frontend.checkout, name='checkout'),
    path('orders/', views_frontend.order_list, name='order_list'),
    path('order/<int:order_id>/', views_frontend.order_detail, name='order_detail'),

    # Отзывы
    path('product/<int:product_id>/review/', views_frontend.add_review, name='add_review'),
]