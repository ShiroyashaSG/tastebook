from django.contrib import admin

from .models import (Favorite, Follow, Ingredient, IngredientRecipe, Recipe,
                     ShoppingCart, ShortLink, Tag)


class RecipeIngredientInline(admin.StackedInline):
    model = IngredientRecipe
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Настройки раздела рецетов админ зоны."""

    list_display = ('pk', 'name', 'author', 'favorites_count')
    list_display_links = ('name', )
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )
    fields = (
        'name',
        'author',
        'tags',
        'text',
        'image',
        'cooking_time'
    )
    inlines = [RecipeIngredientInline]
    readonly_fields = ('favorites_count', )

    def favorites_count(self, obj):
        return obj.favorite_set.count()

    favorites_count.short_description = 'Добавлений в избранное'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Настройки раздела инргедиентов админ зоны."""

    list_display = ('pk', 'name', 'measurement_unit')
    search_fields = ('name', )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Настройки раздела тегов админ зоны."""

    list_display = ('pk', 'name', 'slug')
    search_fields = ('name', )


class BaseRecipeAdmin(admin.ModelAdmin):
    """Базовый класс для админки моделей избранного и корзины."""

    list_display = ('pk', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    readonly_fields = ('user', 'recipe')
    ordering = ('user', )


@admin.register(Favorite)
class FavoriteAdmin(BaseRecipeAdmin):
    """Настройки раздела избранного в админ зоне."""


@admin.register(ShoppingCart)
class ShoppingCartAdmin(BaseRecipeAdmin):
    """Настройки раздела корзины в админ зоне."""


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Настройки раздела подписчиков админ зоны."""

    list_display = ('pk', 'user', 'following')
    search_fields = ('user__username', )
    readonly_fields = ('user', 'following')


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    """Настройки раздела ShortLink в админ зоне."""

    list_display = (
        'pk', 'get_recipe_name', 'get_recipe_id', 'original_url', 'short_url',
    )
    search_fields = ('get_recipe_id', )

    def get_recipe_id(self, obj):
        return obj.recipe.id if obj.recipe else None

    def get_recipe_name(self, obj):
        return obj.recipe.name if obj.recipe else None

    get_recipe_id.short_description = 'Recipe PK'
    get_recipe_name.short_description = 'Название рецепта'
