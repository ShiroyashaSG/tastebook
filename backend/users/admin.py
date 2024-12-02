from django.contrib import admin

from .models import User


class UserAdmin(admin.ModelAdmin):
    """Настройки раздела пользователей админ зоны."""

    list_display = (
        'pk',
        'username',
        'email',
        'first_name',
        'last_name',
        'avatar',
    )
    empty_value_display = 'значение отсутствует'
    list_filter = ('username', )
    search_fields = ('username', 'email')


admin.site.register(User, UserAdmin)
