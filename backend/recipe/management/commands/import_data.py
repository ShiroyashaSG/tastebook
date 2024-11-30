import json

from django.core.management.base import BaseCommand
from recipe.models import Ingredient


class Command(BaseCommand):
    help = 'Import ingredients from a specified JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            nargs='?',
            default='/app/data/ingredients.json',
            help='Path to the JSON file containing ingredients',
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        with open(
            file_path, 'r', encoding='utf-8'
        ) as file:
            data = json.load(file)
            for ingredient_data in data:
                ingredient, created = Ingredient.objects.get_or_create(
                    name=ingredient_data['name'],
                    defaults={
                        'measurement_unit': ingredient_data['measurement_unit']
                    }
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Ингредиент '{ingredient.name}' добавлен"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ингредиент '{ingredient.name}' уже существует"
                        )
                    )
