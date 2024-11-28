from rest_framework import permissions


class IsAuthor(permissions.BasePermission):
    """Разрешение, позволяющее взаимодействовать с данными автору."""

    def has_permission(self, request, view):
        """Проверяет, что пользователь аутентифицирован."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Проверяет, что текущий пользователь является автором объекта.
        """
        return hasattr(obj, 'author') and obj.author == request.user


class IsAnonymous(permissions.BasePermission):
    """Разрешение, позволяющее просматривать
    данные анонимному пользователю.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
