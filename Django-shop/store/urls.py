# store/urls.py
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-quantity/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('order/create/', views.order_create, name='order_create'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('payment/create/<int:order_id>/', views.create_payment, name='create_payment'),
    path('payment/demo/<int:order_id>/', views.demo_payment_page, name='demo_payment_page'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    # path('payment/webhook/', views.payment_webhook, name='payment_webhook'),
]