
from djoser.views import UserViewSet
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import User


class SetEmailRequestSerializer(serializers.Serializer):
    """Тело запроса для смены email."""

    new_username = serializers.EmailField(
        help_text='Новый email. Djoser использует поле new_username, '
        'потому что USERNAME_FIELD = email.',
    )
    current_password = serializers.CharField(
        style={'input_type': 'password'},
        help_text='Текущий пароль пользователя',
    )


class SetEmailResponseSerializer(serializers.Serializer):
    """Ответ при успешной смене email."""

    detail = serializers.CharField(help_text='Сообщение о результате')


@extend_schema_view(
    set_username=extend_schema(
        summary='Смена email',
        description=(
            'Заменяет email текущего пользователя. Так как '
            'USERNAME_FIELD = email, Djoser использует поле new_username '
            'для нового адреса. Требуется текущий пароль. При успехе '
            'возвращает 200 с JSON вместо пустого 204 No Content.'
        ),
        request=SetEmailRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=SetEmailResponseSerializer,
                examples=[
                    OpenApiExample(
                        'Успешная смена',
                        value={'detail': 'Email успешно изменён.'},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description=(
                    'Ошибка валидации — неверный пароль, '
                    'некорректный или занятый email'
                ),
                examples=[
                    OpenApiExample(
                        'Неверный пароль',
                        value={'current_password': 'Неверный пароль.'},
                    ),
                    OpenApiExample(
                        'Email уже занят',
                        value={
                            'new_username': (
                                'Пользователь с таким email уже существует.'
                            )
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(description='Не авторизован'),
        }
    ),
)
class CodeUserViewSet(UserViewSet):
    """UserViewSet djoser с отправкой ответа после смены email."""

    @action(['post'], detail=False, url_path=f'set_{User.USERNAME_FIELD}')
    def set_username(self, request, *args, **kwargs):
        response = super().set_username(request, *args, **kwargs)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            return Response(
                {'detail': 'Email успешно изменён.'},
                status=status.HTTP_200_OK,
            )
        return response
