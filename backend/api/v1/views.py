from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import filters, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import ExerciseFilter
from api.v1.serializers import (
    CodeVerifySerializer,
    ExerciseFullSerializer,
    ResultExerciseSerializer,
    ExerciseSessionSerializer,
    ExerciseShortSerializer,
    HistoryDetailSerializer,
    HistoryListSerializer,
    LoginCodeRequestSerializer,
)
from authentication import services
from exercises.models import Exercise
from backend.exercises.services import ChooseExerciseService
from progress.models import ExerciseSession, UserAnswer


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
        if self.action == 'pass_exercise':
            return ExerciseSessionSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=['post'],
        url_path='pass',
        permission_classes=[IsAuthenticated],
    )

    def _get_config(self, exercise_id: int) -> ExerciseConfig:
        """Вспомогательный метод для получения конфигурации по id задания."""
        exercise_type = get_object_or_404(
            Exercise.objects.values('type'),
            id=exercise_id
        )['type']

        config = EXERCISE_REGISTRY.get(exercise_type)
        if not config:
            raise status.HTTP_400_BAD_REQUEST
        return config

    def pass_exercise(self, request, pk=None):
        """
        Получает результаты прохождения задания
        и в зависимости от его типа валидирует данные
        и проверяет ответ, также сохраняет сессию прохождения задания
        и ответы пользователя.
        :returns ResultExerciseSerializer
        """

        config = self._get_config(pk)
        exercise = config.service.get_exercise(pk)
        serializer = config.write_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clean_data = serializer.validated_data
        task_result = config.service.check_answer(
            exercise, clean_data
        )

        # TODO: добавить обработку ошибок.
        with transaction.atomic():
            session = ExerciseSession.objects.create(
                user=request.user,
                exercise_id=exercise,
                difficulty=exercise.difficulty,
                started_at=clean_data.get('started_at'),
                finished_at=clean_data.get('finished_at'),
                duration_seconds=clean_data.get('duration_seconds'),
                success=task_result.success,
                score=task_result.score
            )
            # TODO: в модели UserAnswer реализовать логику
            #  сохранения ответов пользователя (не в JSON).
            UserAnswer.objects.create(
                session=session,
                answer_data=clean_data.get('answer_data'),
                is_correct=task_result.get('is_correct'),
                response_time=float(clean_data.get('duration_seconds')),
            )

        # TODO: дописать task_result
        return Response(ResultExerciseSerializer(task_result))


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
            .select_related('exercise', 'exercise__type')
            .order_by('-finished_at')
        )


class HistoryDetailView(generics.RetrieveAPIView):
    """История прохождения. Детальный просмотр ответов."""

    serializer_class = HistoryDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExerciseSession.objects.filter(
            user=self.request.user
        ).prefetch_related('answers')


ENUMERATION_MSG = 'Если аккаунт существует, код отправлен на email.'

_VERIFY_CODE_HANDLERS = {
    services.REGISTRATION: services.confirm_registration,
    services.LOGIN: services.login_with_code,
}


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
