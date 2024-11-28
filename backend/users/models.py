from django.contrib.auth.models import AbstractUser
from django.db import models

from backend.constants import MAX_LENGTH_NAME


class User(AbstractUser):
    """Модель пользователя."""

    first_name = models.CharField(
        'Имя',
        max_length=MAX_LENGTH_NAME,
        blank=False,
        null=False
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_LENGTH_NAME,
        blank=False,
        null=False
    )
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
        blank=False,
        null=False,
        error_messages={
            'unique': 'Пользователь с таким email уже существует.',
            'invalid': 'Введите корректный email адрес.',
            'blank': 'Это поле не может быть пустым.'
        }
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='media/users/',
        default='media/users/userpic-icon.2e3faa821bb5398be2c6.jpg',
        blank=True
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username', )

    def __str__(self) -> str:
        return self.username
