"""Фикстуры для pytest."""
from rest_framework.test import APIClient
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class JWTClient(APIClient):
    """Клиент с авторизацией по номеру."""

    def login(self, **credentials):
        """Авторизация по номеру."""
        token_serializer = TokenObtainPairSerializer(
            data=credentials)
        is_valid = token_serializer.is_valid()
        access = token_serializer.validated_data['access']
        self.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        return is_valid

    def force_login(self, user, backend=None):
        """Авторизация юзера, пароль должен быть 1111."""
        user.set_password('1111')
        user.save()
        return self.login(phone=user.phone, password='1111')  # noqa: S106
