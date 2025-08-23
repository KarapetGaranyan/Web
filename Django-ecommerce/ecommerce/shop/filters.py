import django_filters
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    category = django_filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category'
    )
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(field_name='stock', lookup_expr='gt',
                                            exclude=True)
    is_featured = django_filters.BooleanFilter()

    class Meta:
        model = Product
        fields = ['category', 'price_min', 'price_max', 'in_stock', 'is_featured']
