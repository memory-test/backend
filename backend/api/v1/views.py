from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import ExerciseFilter
from api.v1.serializers import (
    CodeVerifySerializer,
    ExerciseSerializer,
    ExerciseSessionSerializer,
    LoginCodeRequestSerializer,
)
from authentication import services
from exercises.models import Exercise
from exercises.services import check_answer
from progress.models import ExerciseSession, UserAnswer


class ExerciseViewSet(ReadOnlyModelViewSet):
    """Вьюсет для чтения объектов модели Exercise."""

    queryset = Exercise.objects.filter(is_active=True)
    serializer_class = ExerciseSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = ExerciseFilter
    search_fields = ('title',)
    ordering_fields = ('title', 'type__name', 'difficulty', 'created_at')

    def get_serializer_class(self):
        if self.action == 'pass_exercise':
            return ExerciseSessionSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=['post'],
        url_path='pass',
        permission_classes=[IsAuthenticated],
    )
    def pass_exercise(self, request, pk=None):
        exercise = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data
        task_result: dict = check_answer(
            exercise, clean_data.get('answer_data')
        )
        # здесь получаем количество попыток пользователя до этой сессии.
        sessions_count: int = (
            ExerciseSession.objects.filter(
                user=request.user, exercise_id=exercise
            ).count()
            + 1
        )

        # будет сохранять в бд 2 записи, иначе ничего.
        # Также чуть позже настроим зедсь логирвоние ошибок,
        # если вдруг записи не сохраняться.
        with transaction.atomic():
            session = ExerciseSession.objects.create(
                user=request.user,
                exercise_id=exercise,
                difficulty=task_result.get('difficulty'),
                started_at=clean_data.get('started_at'),
                finished_at=clean_data.get('finished_at'),
                duration_seconds=clean_data.get('duration_seconds'),
                success=task_result.get('success'),
                score=task_result.get('score'),
                attempts_count=sessions_count,
            )
            UserAnswer.objects.create(
                session=session,
                answer_data=clean_data.get('answer_data'),
                is_correct=task_result.get('is_correct'),
                response_time=float(clean_data.get('duration_seconds')),
            )

        return Response(
            {
                'status': 'success',
                'session_id': session.id,
                'score': session.score,
                'success': session.success,
                'attempts_count': session.attempts_count,
            },
            status=status.HTTP_201_CREATED,
        )


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
