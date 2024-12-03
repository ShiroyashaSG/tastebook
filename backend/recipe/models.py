import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, F, Q

from .constants import (MAX_LENGTH_INGREDIENT_NAME,
                        MAX_LENGTH_INGREDIENT_UNIT,
                        MAX_LENGTH_RECIPE_NAME, MAX_LENGTH_SHORT_URL,
                        MAX_TAG_NAME_SLUG_LENGTH, MIN_VALUE)

User = get_user_model()


class Tag(models.Model):
    """Класс тега."""

    name = models.CharField(
        'Название',
        max_length=MAX_TAG_NAME_SLUG_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        'Слаг',
        max_length=MAX_TAG_NAME_SLUG_LENGTH,
        unique=True,
        blank=True,
        null=False
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиентов."""

    name = models.CharField(
        'Название',
        max_length=MAX_LENGTH_INGREDIENT_NAME
    )

    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_LENGTH_INGREDIENT_UNIT
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        'Название',
        max_length=MAX_LENGTH_RECIPE_NAME
    )
    text = models.TextField(
        'Описание',
    )
    image = models.ImageField(
        'Изображение',
        upload_to='media/recipes/images/',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (минуты)',
        validators=[MinValueValidator(MIN_VALUE)]
    )
    ingredients = models.ManyToManyField(
        Ingredient, through='IngredientRecipe',
        related_name='recipes', verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги'
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """Модель ингредиента."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
        verbose_name="Рецепт"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
        verbose_name="Ингредиент"
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(MIN_VALUE)]
    )

    class Meta:
        verbose_name = "ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient} для {self.recipe}'


class Follow(models.Model):
    """Модель подписок."""

    user = models.ForeignKey(
        User, related_name='following', on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        User, related_name='followers', on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(user=F('following')),
                name='user_not_equal_to_following'
            ),
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='user_following'
            ),
        ]
        verbose_name = 'подписчик'
        verbose_name_plural = 'Подписчики'

    def __str__(self) -> str:
        return f'{self.user} подписан на {self.following}'


class ShoppingCartFavorite(models.Model):
    """Базовая модель для списка покупок и избранного."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user} {self.recipe}'


class ShoppingCart(ShoppingCartFavorite):
    """Модель списка покупок."""

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]


class Favorite(ShoppingCartFavorite):
    """Модель избранных рецептов."""

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]


class ShortLink(models.Model):
    """Модель коротких ссылок."""

    original_url = models.URLField(
        'Оригинальная ссылка'
    )
    short_url = models.CharField(
        'Сокращенная ссылка',
        max_length=MAX_LENGTH_SHORT_URL,
        unique=True,
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='short_link'
    )

    class Meta:
        verbose_name = 'короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def __str__(self):
        return f'Короткая ссылка для рецепта: {self.recipe.name}'

    def save(self, *args, **kwargs):
        if not self.short_url:
            self.short_url = self.generate_unique_short_url()
        super().save(*args, **kwargs)

    def generate_short_url(self):
        """Генерация случайного 10-символьного кода"""
        return ''.join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )

    def generate_unique_short_url(self):
        """Генерация уникальной случайной ссылки"""
        short_code = self.generate_short_url()
        while ShortLink.objects.filter(short_url=short_code).exists():
            short_code = self.generate_short_url()
        return short_code
