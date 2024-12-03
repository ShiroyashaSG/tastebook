from django.db.models import Sum

from recipe.models import IngredientRecipe, ShoppingCart


def get_shopping_cart_ingredients(request):
    """Генерация и скачивание списка покупок в формате CSV."""
    shopping_cart = ShoppingCart.objects.filter(
        user=request.user
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
