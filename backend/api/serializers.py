import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer
from recipe.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                           Recipe, ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .constants import MAX_LENGTH_EMAIL, MAX_LENGTH_NAME, REGEX_USERNAME

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле сериализатора для обработки изображений в формате Base64."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class CustomUserMixin:
    """Миксин для модели пользователя."""

    username = serializers.RegexField(
        regex=REGEX_USERNAME,
        max_length=MAX_LENGTH_NAME,
        required=True,
        validators=[UniqueValidator(
            queryset=User.objects.all(),
            message='Пользователь с таким именем username уже существует.'
        )],
        error_messages={
            'invalid': (
                'Имя пользователя может содержать только буквы, цифры ',
                'и символы @/./+/-/_'
            )
        }
    )
    email = serializers.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='Пользователь с таким именем email уже существует.'
            )
        ]
    )
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_NAME, required=True,
    )
    last_name = serializers.CharField(
        max_length=MAX_LENGTH_NAME, required=True,
    )


class CustomUserSerializer(CustomUserMixin, serializers.ModelSerializer):
    """Сериализатор для модели пользователя."""

    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )
        read_only_fields = ('avatar', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return obj.followers.filter(user=user).exists()


class RecipeListFollowSerializer(serializers.Serializer):
    recipes_limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        error_messages={
            'min_value': 'Минимальное количество рецептов: 1.',
            'max_value': 'Максимальное количество рецептов: 100.',
        }
    )

    def validate(self, data):
        user = self.context['request'].user
        user_to_subscribe = self.context.get('user_to_subscribe')

        if user_to_subscribe:
            if user == user_to_subscribe:
                raise serializers.ValidationError(
                    {"detail": "Нельзя подписываться на самого себя"}
                )

            if Follow.objects.filter(
                user=user, following=user_to_subscribe
            ).exists():
                raise serializers.ValidationError(
                    {"detail": "Вы уже подписаны на этого пользователя"}
                )

        return data


class CustomUserCreateSerializer(CustomUserMixin, UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'password'
        )


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара пользователя."""

    avatar = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar', )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов и связанных с ними рецептов."""

    name = serializers.CharField(
        read_only=True, source='ingredient.name'
    )
    measurement_unit = serializers.CharField(
        read_only=True, source='ingredient.measurement_unit'
    )
    id = serializers.IntegerField(source='ingredient.id')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор рецептов."""

    ingredients = IngredientRecipeSerializer(
        source='ingredient_recipes', required=True, many=True
    )
    image = Base64ImageField(required=True, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time'
        )

    def validate_cooking_time(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Время приготовления должно быть больше нуля."
            )
        return value

    def validate_ingredients(self, value):
        """Валидация списка ингредиентов."""
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым."
            )

        unique_ids = set()
        item_ids = []

        for item in value:
            item_id = item['ingredient']['id']
            if item_id in unique_ids:
                raise serializers.ValidationError(
                    "Ингредиенты должны быть уникальными."
                )

            if item['amount'] <= 0:
                raise serializers.ValidationError(
                    "Количество ингредиента должно быть больше нуля."
                )
            unique_ids.add(item_id)
            item_ids.append(item_id)

        existing_items = Ingredient.objects.filter(id__in=item_ids)
        missing_ids = set(item_ids) - set(
            existing_items.values_list('id', flat=True)
        )
        if missing_ids:
            raise serializers.ValidationError(
                f"Ингредиенты {', '.join(map(str, missing_ids))} не найдены."
            )

        return value

    def validate_tags(self, value):
        """Валидация списка ингредиентов."""
        if not value:
            raise serializers.ValidationError(
                "Список тегов не может быть пустым."
            )

        unique_name = set()
        item_name = []

        for item in value:
            if item in unique_name:
                raise serializers.ValidationError(
                    "Теги должны быть уникальными."
                )
            unique_name.add(item)
            item_name.append(item)

        existing_items = Tag.objects.filter(name__in=item_name)
        missing_names = set(item_name) - set(existing_items)
        if missing_names:
            raise serializers.ValidationError(
                f"Теги: {', '.join(map(str, missing_names))} не найдены."
            )

        return value


class RecipeCreateUpdateSerializer(RecipeBaseSerializer):
    """Сериализатор создания и обновления рецепта."""

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredient_recipes')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data['ingredient']['id']

            amount = ingredient_data['amount']

            ingredient = Ingredient.objects.get(id=ingredient_id)
            IngredientRecipe.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        required_fields = [
            'name', 'text', 'cooking_time',
            'tags', 'ingredient_recipes'
        ]
        for field in required_fields:
            if field not in validated_data:
                raise serializers.ValidationError(
                    {field: f'Поле {field} обязательно.'}
                )
        instance.name = validated_data.get('name')
        instance.text = validated_data.get('text')
        instance.cooking_time = validated_data.get('cooking_time')
        instance.image = validated_data.get('image', instance.image)
        ingredients_data = validated_data.pop('ingredient_recipes')
        tags = validated_data.pop('tags')
        instance.tags.set(tags)
        for ingredient in ingredients_data:
            ingredient_id = ingredient['ingredient']['id']

            amount = ingredient['amount']

            ingredient = Ingredient.objects.get(id=ingredient_id)
            existing_ingredient_recipe = IngredientRecipe.objects.filter(
                recipe=instance, ingredient=ingredient
            ).first()
            if existing_ingredient_recipe:
                existing_ingredient_recipe.amount = amount
                existing_ingredient_recipe.save()
            else:
                IngredientRecipe.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=amount
                )
        instance.save()
        return instance


class RecipeSerializer(RecipeBaseSerializer):
    """Сериализатор рецептов."""

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(required=True, many=True)
    author = CustomUserSerializer()

    class Meta(RecipeBaseSerializer.Meta):
        fields = RecipeBaseSerializer.Meta.fields + (
            'id', 'author', 'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeShortSerializer(RecipeBaseSerializer):
    """Сериализатор для краткой информации о рецепте."""
    class Meta(RecipeBaseSerializer.Meta):
        fields = ('id', 'name', 'image', 'cooking_time')


class UserFollowSerializer(CustomUserSerializer):
    """Сериализатор подписок и связанных с ними рецептов."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )
        read_only_fields = CustomUserSerializer.Meta.read_only_fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes.count()

    def get_recipes(self, obj):
        """Получение рецептов в соответствии с ограничениев."""
        recipes_limit = self.context.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]
        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор списка покупок."""

    class Meta:
        model = ShoppingCart


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор избранного."""

    class Meta:
        model = Favorite


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор подписок."""

    class Meta:
        model = Follow
