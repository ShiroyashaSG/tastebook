import json
import os

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
        if os.path.exists(file_path):
            try:
                with open(
                    file_path, 'r', encoding='utf-8'
                ) as file:
                    data = json.load(file)
                    added_count = 0
                    existing_count = 0
                    for ingredient_data in data:
                        ingredient, created = Ingredient.objects.get_or_create(
                            name=ingredient_data['name'],
                            defaults={
                                'measurement_unit': ingredient_data[
                                    'measurement_unit'
                                ]
                            }
                        )
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    'Ингредиент '
                                    f'"{ingredient.name}" добавлен'
                                )
                            )
                            added_count += 1
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    'Ингредиент '
                                    f'"{ingredient.name}" уже существует'
                                )
                            )
                            existing_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        'Импорт завершен: добавлено '
                        f'{added_count} новых ингредиентов, '
                        f'уже существующих — {existing_count}.'
                    )
                )
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(
                    "Ошибка при чтении JSON файла"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Произошла ошибка: {e}"))
        else:
            print(f"Файл {file_path} не найден!")
