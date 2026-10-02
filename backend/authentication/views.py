from djoser.views import UserViewSet
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from users.models import User

from .djoser import (
    AvatarUploadSerializer,
    SetEmailRequestSerializer,
    SetEmailResponseSerializer,
)


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
        },
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

    @extend_schema(
        summary='Загрузка аватара',
        description=(
            'Загружает или заменяет аватар текущего пользователя. '
            'Тело запроса — multipart/form-data с единственным полем '
            'avatar (файл изображения). Полная замена: новый файл '
            'заменяет старый, частичная загрузка (только часть '
            'изображения) не поддерживается.'
        ),
        request={
            'multipart/form-data': AvatarUploadSerializer,
        },
        responses={
            200: AvatarUploadSerializer,
            400: OpenApiResponse(
                response={
                    'type': 'object',
                    'description': (
                        'Ошибка валидации файла (не изображение, '
                        'повреждён и т.п.): {"avatar": ["..."]}.'
                    ),
                    'properties': {},
                    'additionalProperties': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                description='Ошибка валидации',
            ),
            401: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {'detail': {'type': 'string'}},
                },
                description='Не авторизован',
            ),
        },
        examples=[
            OpenApiExample(
                'Успешная загрузка',
                value={'avatar': 'http://example.com/media/avatars/photo.jpg'},
                response_only=True,
            ),
        ],
    )
    @action(
        ['patch'],
        detail=False,
        url_path='me/avatar',
        parser_classes=[MultiPartParser, FormParser],
    )
    def avatar(self, request, *args, **kwargs):
        """PATCH /users/me/avatar/ — загрузка/смена аватара."""
        serializer = AvatarUploadSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
