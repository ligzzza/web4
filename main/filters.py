from django_filters import rest_framework as filters
from .models import MasterClass


class MasterClassFilter(filters.FilterSet):
    """Фильтрация мастер-классов для API"""

    # Фильтр по цене (от и до)
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Фильтр по городу (частичное совпадение, без учёта регистра)
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')

    # Фильтр по категории (по slug или id)
    category = filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    category_id = filters.NumberFilter(field_name='category__id', lookup_expr='exact')

    # Фильтр по формату
    format = filters.ChoiceFilter(choices=MasterClass.FORMAT_CHOICES)

    # Фильтр по статусу
    status = filters.ChoiceFilter(choices=MasterClass.STATUS_CHOICES)

    class Meta:
        model = MasterClass
        fields = ['city', 'category', 'category_id', 'format', 'status']