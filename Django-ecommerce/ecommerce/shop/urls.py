# shop/urls.py - основные URL для API mobile
from django.urls import path
from . import views

app_name = 'shop_api'

urlpatterns = [
    # API mobile endpoints
    # Категории
    path('api/categories/', views.CategoryListView.as_view(), name='category-list'),

    # Товары
    path('api/products/', views.ProductListView.as_view(), name='product-list'),
    path('api/products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Корзина
    path('api/cart/', views.CartView.as_view(), name='cart'),
    path('api/cart/add/', views.add_to_cart, name='add-to-cart'),
    path('api/cart/update/<int:item_id>/', views.update_cart_item, name='update-cart-item'),
    path('api/cart/remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),

    # Заказы
    path('api/orders/', views.OrderListView.as_view(), name='order-list'),
    path('api/orders/create/', views.create_order, name='create-order'),
    path('api/orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),

    # Отзывы
    path('api/products/<int:product_id>/reviews/', views.ReviewListCreateView.as_view(), name='product-reviews'),
]