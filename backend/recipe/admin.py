from django.contrib import admin

from .models import (Favorite, Follow, Ingredient, Recipe, ShoppingCart,
                     ShortLink, Tag)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Настройки раздела рецетов админ зоны."""

    list_display = ('name', 'author', 'favorites_count')
    list_display_links = ('name',)
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    fields = ('name', 'author', 'tags', 'favorites_count')
    readonly_fields = ('favorites_count',)

    def favorites_count(self, obj):
        return obj.favorite_set.count()

    favorites_count.short_description = 'Добавлений в избранное'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Настройки раздела тегов админ зоны."""

    list_display = ('pk', 'name', 'measurement_unit')
    search_fields = ('name', )


admin.site.register(Tag)
admin.site.register(Favorite)
admin.site.register(Follow)
admin.site.register(ShoppingCart)
admin.site.register(ShortLink)
