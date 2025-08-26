# from django.urls import path
# from . import views
#
# app_name = 'accounts'
#
# urlpatterns = [
#     path('register/', views.register, name='register'),
#     path('login/', views.user_login, name='login'),
#     path('logout/', views.user_logout, name='logout'),
#     path('profile/', views.profile, name='profile'),
#     path('order/<int:order_id>/', views.order_detail, name='order_detail'),
# ]

# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),
]