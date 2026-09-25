from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import filters, generics, status
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import ExerciseFilter
from api.v1.schema.params import (
    RU_LIMIT_PARAM,
    RU_ORDERING_PARAM,
    RU_PAGE_PARAM,
    RU_SEARCH_PARAM,
)
from api.v1.serializers import (
    ChoiceCheckSerializer,
    CodeVerifySerializer,
    ExerciseFullSerializer,
    ExerciseShortSerializer,
    HistoryDetailSerializer,
    HistoryListSerializer,
    InputCheckSerializer,
    LoginCodeRequestSerializer,
    MatchingCheckSerializer,
    ResultExerciseSerializer,
)
from authentication import services
from authentication.models import EmailCode
from exercises.models import Exercise
from progress.models import ExerciseSession, UserAttempt

from .registry import EXERCISE_REGISTRY, ExerciseConfig


@extend_schema_view(
    list=extend_schema(
        summary='Список заданий',
        description=(
            'Возвращает пагинированный список активных заданий с '
            'фильтрацией по типу, сложности и поиском по названию.'
        ),
        parameters=[
            RU_SEARCH_PARAM,
            RU_ORDERING_PARAM,
            RU_LIMIT_PARAM,
            RU_PAGE_PARAM,
        ],
    ),
    retrieve=extend_schema(
        summary='Детальное задание',
        description=(
            'Возвращает полное описание задания со всеми ответами '
            '(без пометки правильности, если запрос от студента).'
        ),
    ),
)
class ExerciseViewSet(ReadOnlyModelViewSet):
    """Вьюсет для чтения объектов модели Exercise."""

    queryset = Exercise.objects.filter(is_active=True)
    serializer_class = ExerciseFullSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = ExerciseFilter
    search_fields = ('title',)
    ordering_fields = ('title', 'type', 'difficulty', 'created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return ExerciseShortSerializer
        return super().get_serializer_class()

    def _get_config(self, exercise_id: int) -> ExerciseConfig:
        """Вспомогательный метод для получения конфигурации по id задания."""
        exercise_type = get_object_or_404(
            Exercise.objects.values('type'), id=exercise_id
        )['type']

        config = EXERCISE_REGISTRY.get(exercise_type)
        if not config:
            raise drf_serializers.ValidationError(
                {'type': f'Тип задания "{exercise_type}" не поддерживается.'}
            )

        return config

    @extend_schema(
        summary='Прохождение задания',
        description=(
            'Принимает ответ пользователя, проверяет его и сохраняет '
            'результат. Тело запроса зависит от типа задания: choice — '
            'ChoiceCheckSerializer (answers_ids), input — '
            'InputCheckSerializer (answers). Возвращает оценку и признак '
            'успешности.'
        ),
        request=PolymorphicProxySerializer(
            component_name='PassRequest',
            serializers=[
                ChoiceCheckSerializer,
                InputCheckSerializer,
                MatchingCheckSerializer,
            ],
            resource_type_field_name=None,
        ),
        examples=[
            OpenApiExample(
                'Пример запроса (choice)',
                value={
                    'started_at': '2026-09-07T14:30:00Z',
                    'finished_at': '2026-09-07T14:32:15Z',
                    'duration_seconds': 135,
                    'answers_ids': [101, 103],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Пример запроса (input, один ответ)',
                value={
                    'started_at': '2026-09-07T14:30:00Z',
                    'finished_at': '2026-09-07T14:30:10Z',
                    'duration_seconds': 10,
                    'answers': ['Париж'],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Пример запроса (input, список ответов)',
                value={
                    'started_at': '2026-09-07T14:30:00Z',
                    'finished_at': '2026-09-07T14:30:15Z',
                    'duration_seconds': 15,
                    'answers': ['Стол', 'Окно', 'Дверь', 'Лампа'],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Пример запроса (input, свободная форма)',
                value={
                    'started_at': '2026-09-07T14:30:00Z',
                    'finished_at': '2026-09-07T14:30:20Z',
                    'duration_seconds': 20,
                    'answers': [
                        'Нужно не торопиться, тогда быстрее дойдёшь до цели'
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Пример запроса (matching)',
                value={
                    'started_at': '2026-09-07T14:30:00Z',
                    'finished_at': '2026-09-07T14:30:30Z',
                    'duration_seconds': 30,
                    'pairs': [
                        {'first_id': 1, 'second_id': 1},
                        {'first_id': 2, 'second_id': 2},
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Результат прохождения',
                value={'score': 0.67, 'success': False},
                response_only=True,
            ),
        ],
        responses={
            200: ResultExerciseSerializer,
            400: OpenApiResponse(
                response={
                    'type': 'object',
                    'description': (
                        'Ошибка валидации: либо {"detail": "..."} — общая '
                        'ошибка, либо {"<поле>": ["..."]} — ошибка '
                        'конкретного поля (answers_ids, answers).'
                    ),
                    'properties': {'detail': {'type': 'string'}},
                    'additionalProperties': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                description='Ошибка валидации',
            ),
            404: inline_serializer(
                'PassExerciseNotFound',
                {'detail': drf_serializers.CharField()},
            ),
        },
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='pass',
        permission_classes=[IsAuthenticated],
    )
    def pass_exercise(self, request, pk=None):
        config = self._get_config(pk)
        exercise = config.service.get_exercise(pk)
        serializer = config.write_serializer(
            data=request.data, context={'exercise': exercise}
        )
        serializer.is_valid(raise_exception=True)
        clean_data = serializer.validated_data
        task_result = config.service.check_answer(exercise, clean_data)
        exercise_snapshot = ExerciseFullSerializer(
            exercise, context={'show_correct': True}
        ).data
        complete_attempt_data = {
            'exercise_snapshot': exercise_snapshot,
            'user_response': {
                'user_choice': clean_data,
                'result': task_result.success,
            },
        }

        with transaction.atomic():
            session = ExerciseSession.objects.create(
                user=request.user,
                exercise=exercise,
                difficulty=exercise.difficulty,
                started_at=clean_data.get('started_at'),
                finished_at=clean_data.get('finished_at'),
                duration_seconds=clean_data.get('duration_seconds'),
                success=task_result.success,
                score=task_result.score,
            )
            UserAttempt.objects.create(
                session=session,
                answer_data=complete_attempt_data,
            )
        return Response(ResultExerciseSerializer(task_result).data)


@extend_schema_view(
    list=extend_schema(
        summary='История прохождения — список',
        description=(
            'Возвращает пагинированный список завершённых сессий '
            'пользователя с краткой информацией.'
        ),
        parameters=[RU_LIMIT_PARAM, RU_PAGE_PARAM],
    ),
)
class HistoryListView(generics.ListAPIView):
    """История прохождения. Список завершенных упражнений."""

    serializer_class = HistoryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ExerciseSession.objects.filter(
                user=self.request.user,
                finished_at__isnull=False,
            )
            .select_related('exercise')
            .order_by('-finished_at')
        )


@extend_schema(
    summary='История прохождения — детали',
    description=(
        'Возвращает детальную информацию о конкретной сессии: метаданные, '
        'оценку и полные данные попытки (answer_data).'
    ),
)
class HistoryDetailView(generics.RetrieveAPIView):
    """История прохождения. Детальный просмотр ответов."""

    serializer_class = HistoryDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExerciseSession.objects.filter(
            user=self.request.user
        ).select_related('exercise', 'attempt')


ENUMERATION_MSG = 'Если аккаунт существует, код отправлен на email.'

_VERIFY_CODE_HANDLERS = {
    EmailCode.Purpose.REGISTRATION: services.confirm_registration,
    EmailCode.Purpose.LOGIN: services.login_with_code,
}


@extend_schema(
    summary='Запрос кода для входа',
    description=(
        'Отправляет код подтверждения на email. Ответ всегда одинаковый '
        '(анти-enumeration): если аккаунт существует, код отправлен.'
    ),
    request=LoginCodeRequestSerializer,
    responses={
        200: inline_serializer(
            'LoginCodeRequestResponse',
            {'detail': drf_serializers.CharField()},
        ),
        429: inline_serializer(
            'LoginCodeRequestThrottled',
            {'detail': drf_serializers.CharField()},
        ),
    },
)
class LoginCodeRequestView(APIView):
    """Запрос кода для входа — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.request_login_code(serializer.validated_data['email'])
        except (services.CooldownError, services.RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({'detail': ENUMERATION_MSG})


@extend_schema(
    summary='Подтверждение кода и получение JWT',
    description=(
        'Проверяет код подтверждения и возвращает пару '
        "access/refresh JWT-токенов. purpose='registration' — завершение "
        "регистрации, purpose='login' — вход по коду."
    ),
    request=CodeVerifySerializer,
    responses={
        200: inline_serializer(
            'CodeVerifyResponse',
            {
                'access': drf_serializers.CharField(),
                'refresh': drf_serializers.CharField(),
            },
        ),
        400: inline_serializer(
            'CodeVerifyError',
            {'detail': drf_serializers.CharField()},
        ),
    },
)
class CodeVerifyView(APIView):
    """Подтверждение кода (регистрация/вход) с выдачей JWT."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CodeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purpose = serializer.validated_data['purpose']
        handler = _VERIFY_CODE_HANDLERS[purpose]
        try:
            _, tokens = handler(
                serializer.validated_data['email'],
                serializer.validated_data['code'],
            )
        except services.CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(tokens)
