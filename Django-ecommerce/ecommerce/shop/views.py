from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import *
from .serializers import *
from .filters import ProductFilter
from django.shortcuts import render

def home(request):
    return render(request, 'shop/home.html')

def search(request):
    query = request.GET.get('q', '')
    if query:
        # Здесь добавьте логику поиска
        # Например, поиск по продуктам
        results = []  # Замените на реальный поиск
        context = {
            'query': query,
            'results': results
        }
        return render(request, 'shop/search_results.html', context)
    else:
        return render(request, 'shop/search.html')

def profile(request):
    return render(request, 'shop/products.html')

def products(request):
    # Здесь получите продукты из базы данных
    products = Product.objects.all()  # Замените на вашу модель
    context = {
        'products': products
    }
    return render(request, 'shop/products.html', context)

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True, parent=None)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'short_description']
    ordering_fields = ['price', 'created_at', 'rating']
    ordering = ['-created_at']

    def get_queryset(self):
        """Оптимизированный запрос товаров"""
        return Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        """Оптимизированный запрос для деталей товара"""
        return Product.objects.filter(is_active=True).select_related('category').prefetch_related('images',
                                                                                                  'reviews__user')


class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        if not created:
            # Оптимизируем запрос корзины
            cart = Cart.objects.prefetch_related(
                'items__product__category',
                'items__product__images'
            ).get(user=self.request.user)
        return cart


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Добавьте эту строку
def add_to_cart(request):
    serializer = AddToCartSerializer(data=request.data)
    if serializer.is_valid():
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        product = get_object_or_404(Product, id=product_id, is_active=True)

        if product.stock < quantity:
            return Response({'error': 'Недостаточно товара в наличии'},
                            status=status.HTTP_400_BAD_REQUEST)

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock:
                return Response({'error': 'Недостаточно товара в наличии'},
                                status=status.HTTP_400_BAD_REQUEST)
            cart_item.save()

        return Response({'message': 'Товар добавлен в корзину'},
                        status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = request.data.get('quantity', 1)

    if quantity <= 0:
        cart_item.delete()
        return Response({'message': 'Товар удален из корзины'})

    if quantity > cart_item.product.stock:
        return Response({'error': 'Недостаточно товара в наличии'},
                        status=status.HTTP_400_BAD_REQUEST)

    cart_item.quantity = quantity
    cart_item.save()

    return Response({'message': 'Количество товара обновлено'})


@api_view(['DELETE'])
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return Response({'message': 'Товар удален из корзины'})


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  # Добавьте эту строку

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  # Добавьте эту строку

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Добавьте эту строку
@transaction.atomic
def create_order(request):
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        return Response({'error': 'Корзина пуста'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Проверяем наличие товаров
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            return Response({'error': f'Недостаточно товара {item.product.name} в наличии'},
                            status=status.HTTP_400_BAD_REQUEST)

    serializer = CreateOrderSerializer(data=request.data)
    if serializer.is_valid():
        # Рассчитываем стоимость доставки (можно добавить логику)
        delivery_cost = 300  # Фиксированная стоимость доставки

        order = serializer.save(
            user=request.user,
            subtotal=cart.total_price,
            delivery_cost=delivery_cost,
            total=cart.total_price + delivery_cost
        )

        # Создаем позиции заказа
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            # Уменьшаем остаток товара
            item.product.stock -= item.quantity
            item.product.save()

        # Очищаем корзину
        cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return Review.objects.filter(product_id=product_id, is_verified=True)

    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        serializer.save(user=self.request.user, product=product)