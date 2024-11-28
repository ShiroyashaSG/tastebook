from django_filters import rest_framework as filters
from recipe.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """Фильтры для рецептов."""

    is_favorited = filters.BooleanFilter(
        method='filter_is_favorited',
        label='Избранные рецепты'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
        label='Рецепты в списке покупок'
    )
    author = filters.NumberFilter(field_name='author__id', label='Автор')
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        label='Теги',
        to_field_name='slug'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        """Фильтр избранного."""
        if value:
            return queryset.filter(favorite_set__isnull=False)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтр списка покупок."""
        if value:
            return queryset.filter(shoppingcart_set__isnull=False)
        return queryset
