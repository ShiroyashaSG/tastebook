import csv
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, Sum, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipe.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                           Recipe, ShoppingCart, ShortLink, Tag)
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .filters import RecipeFilter
from .paginations import CustomPagination
from .permissions import IsAnonymous, IsAuthor
from .serializers import (IngredientSerializer, RecipeCreateUpdateSerializer,
                          RecipeSerializer, RecipeShortSerializer,
                          TagSerializer, UserAvatarSerializer,
                          UserFollowSerializer)

User = get_user_model()


@api_view(['GET'])
def redirect_short_link(request, short_code):
    """Обработка короткой ссылки и перенаправление на рецепт."""
    short_link = get_object_or_404(ShortLink, short_url=short_code)
    return redirect(short_link.original_url)


class CustomUserViewSet(UserViewSet):
    """Представление для добавления и удаления аватара пользоввателя."""

    queryset = User.objects.all()
    pagination_class = CustomPagination
    permission_classes = (
        permissions.IsAdminUser | permissions.IsAuthenticated,
    )

    def get_permissions(self):
        if self.action in ('retrieve'):
            self.permission_classes = [IsAnonymous, ]
        return super().get_permissions()

    @action(
        methods=['put', 'delete'],
        detail=False,
        url_path='me/avatar',
        serializer_class=UserAvatarSerializer
    )
    def avatar_add_destroy(self, request):
        """Добавление и удаление аватара пользователя."""
        user = request.user
        if request.method == 'PUT':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.avatar = serializer.validated_data.get('avatar')
            user.save()
            response_serializer = self.get_serializer(user)
            return Response(
                response_serializer.data, status=status.HTTP_200_OK
            )
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'detail': 'Аватар уже отсутствует.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='subscribe'
    )
    def user_subscribe(self, request, id):
        """Подписаться на пользователя/удалить подписку."""
        user = request.user
        user_to_subscribe = get_object_or_404(User, id=id)

        if request.method == 'POST':
            recipes_limit = request.query_params.get('recipes_limit')
            try:
                recipes_limit = int(recipes_limit) if recipes_limit else 1
            except ValueError:
                return Response(
                    {"detail": "Параметр 'recipes_limit' должен быть числом."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if user == user_to_subscribe:
                return Response(
                    {"detail": "Нельзя подписываться на самого себя"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif Follow.objects.filter(
                user=user, following=user_to_subscribe
            ).exists():
                return Response(
                    {"detail": "Вы уже подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, following=user_to_subscribe)
            serializer = UserFollowSerializer(
                user_to_subscribe,
                context={
                    'request': request,
                    'recipes_limit': recipes_limit
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscription_exists = Follow.objects.filter(
                user=user, following=user_to_subscribe
            ).exists()

            if not subscription_exists:
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.filter(
                user=user, following=user_to_subscribe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        url_path='subscriptions',
        permission_classes=(
            permissions.IsAuthenticated | permissions.IsAdminUser,
        )
    )
    def user_subscriptions(self, request):
        """Получение подписок пользователя."""
        recipes_limit = request.query_params.get('recipes_limit', None)

        try:
            recipes_limit = int(recipes_limit) if recipes_limit else 1
        except ValueError:
            # Если не удалось преобразовать в целое число, можно вернуть ошибку
            return Response(
                {"detail": "Параметр 'recipes_limit' должен быть числом."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Получаем подписки текущего пользователя
        subscriptions = Follow.objects.filter(
            user=request.user
        ).select_related('following')

        # Извлекаем список подписанных пользователей
        subscribed_users = User.objects.filter(
            id__in=subscriptions.values_list('following_id', flat=True)
        )

        # Применяем пагинацию
        page = self.paginate_queryset(subscribed_users)
        if page is not None:
            serializer = UserFollowSerializer(
                page,
                many=True,
                context={
                    'request': request,
                    'recipes_limit': recipes_limit,
                }
            )
            return self.get_paginated_response(serializer.data)


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Получение ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny, )

    def get_queryset(self):
        queryset = super().get_queryset()
        name_filter = self.request.query_params.get('name')

        if name_filter:
            queryset = queryset.filter(
                Q(name__istartswith=name_filter) | Q(
                    name__icontains=name_filter
                )
            )

            queryset = queryset.order_by(
                Case(
                    When(name__istartswith=name_filter, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                'name'
            )

        return queryset


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """Получение тэгов."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny, )


class RecipeViewSet(viewsets.ModelViewSet):
    """Представление для рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [
                permissions.IsAuthenticated | permissions.IsAdminUser,
            ]
        elif self.request.method in ['PATCH', 'DELETE']:
            permission_classes = [IsAuthor]
        elif self.request.method in permissions.SAFE_METHODS:
            permission_classes = [IsAnonymous, ]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        base_url = f"https://{self.request.get_host()}"
        full_path = self.request.path
        original_url = f'{base_url}{full_path}'
        short_link = ShortLink(original_url=original_url, recipe=recipe)
        short_link.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        recipe = serializer.instance
        recipe_serializer = RecipeSerializer(
            recipe,
            context={'request': self.request}
        )
        return Response(recipe_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Переопределяет метод update для возврата кастомного ответа."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        recipe = serializer.instance
        recipe_serializer = RecipeSerializer(
            recipe,
            context={'request': self.request}
        )
        return Response(recipe_serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['get'],
        detail=True,
        url_path='get-link'
    )
    def get_short_link(self, request, pk):
        """Получение короткой ссылки."""
        recipe = get_object_or_404(Recipe, id=pk)
        short_link = get_object_or_404(ShortLink, recipe=recipe)
        base_url = f"https://{request.get_host()}"
        full_url = urljoin(base_url, f"/s/{short_link.short_url}")
        return Response({'short-link': full_url})

    def get_shopping_cart_ingredients(self):
        """Генерация и скачивание списка покупок в формате CSV."""
        shopping_cart = ShoppingCart.objects.filter(
            user=self.request.user
        ).prefetch_related('recipe')
        ingredients = (
            IngredientRecipe.objects.filter(
                recipe__in=[item.recipe for item in shopping_cart]).values(
                    'ingredient__name', 'ingredient__measurement_unit'
            ).annotate(total_amount=Sum('amount'))
        )
        return [
            {
                "name": ingredient['ingredient__name'],
                "measurement_unit": ingredient['ingredient__measurement_unit'],
                "amount": ingredient['total_amount'],
            }
            for ingredient in ingredients
        ]

    @action(
        methods=['get'],
        detail=False,
        url_path='download_shopping_cart',
        permission_classes=(
            permissions.IsAuthenticated | permissions.IsAdminUser,
        )
    )
    def download_shopping_cart(self, request):
        """Генерация и скачивание списка покупок в формате CSV."""
        items = self.get_shopping_cart_ingredients()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.csv"'
        )
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Название', 'Единица измерения', 'Количество'])
        for item in items:
            writer.writerow([
                item['name'],
                item['measurement_unit'],
                item['amount']
            ])

        return response

    def handle_action(
        self, request, pk, model, error_message
    ):
        """Общий метод для обработки добавления/удаления рецепта."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if not model.objects.filter(user=user, recipe=recipe).exists():
                model.objects.create(user=user, recipe=recipe)
                serializer = RecipeShortSerializer(recipe)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                {"detail": "Этот рецепт уже добавлен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'DELETE':
            item = model.objects.filter(user=user, recipe=recipe)
            if item.exists():
                item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=['post', 'delete'], detail=True, url_path='favorite')
    def favorite_recipe(self, request, pk=None):
        """Добавление/удаление рецепта из избранного."""
        return self.handle_action(
            request=request,
            pk=pk,
            model=Favorite,
            error_message="Рецепт не найден в избранном"
        )

    @action(methods=['post', 'delete'], detail=True, url_path='shopping_cart')
    def shopping_cart_recipe(self, request, pk=None):
        """Добавление/удаление рецепта из корзины."""
        return self.handle_action(
            request=request,
            pk=pk,
            model=ShoppingCart,
            error_message="Рецепт не найден в списке покупок"
        )
