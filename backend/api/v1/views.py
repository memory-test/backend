from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import ExerciseFilter
from api.v1.serializers import (
    CodeRequestSerializer,
    CodeVerifySerializer,
    ExerciseSerializer,
    ResultExerciseSerializer,
    ExerciseSessionSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UserSerializer,
)
from backend.exercises.models import Exercise
from backend.exercises.services import ChooseExerciseService
from backend.progress.models import ExerciseSession, UserAnswer
from .registry import EXERCISE_REGISTRY
from authentication import services
from backend.exercises.models import Exercise
from exercises.services import check_answer
from progress.models import ExerciseSession, UserAnswer


class ExerciseView(viewsets.ViewSet):
    """Контроллер для выполнения задания"""

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

    def list(self, request):
        queryset = Exercise.objects.filter(is_active=True)
        serializer = ExerciseSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Отдает структуру задания.
        """
        config = self._get_config(pk)
        exercise = config.service.get_exercise(pk)
        serializer = config.read_serializer(exercise, context={'exercise': exercise})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='pass',
        permission_classes=[IsAuthenticated],
    )
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


ENUMERATION_MSG = 'Если аккаунт существует, код отправлен на email.'

_REQUEST_CODE_HANDLERS = {
    services.REGISTRATION: services.resend_registration_code,
    services.LOGIN: services.request_login_code,
    services.PASSWORD_RESET: services.start_password_reset,
}

_VERIFY_CODE_HANDLERS = {
    services.REGISTRATION: services.confirm_registration,
    services.LOGIN: services.login_with_code,
}


class RegisterView(APIView):
    """Регистрация пользователя и отправка кода подтверждения."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.start_registration(**serializer.validated_data)
        except (services.CooldownError, services.RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response(
            {
                'detail': 'Код подтверждения отправлен на email.',
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class CodeRequestView(APIView):
    """Запрос кода (регистрация/вход/сброс) — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purpose = serializer.validated_data['purpose']
        handler = _REQUEST_CODE_HANDLERS[purpose]
        try:
            handler(serializer.validated_data['email'])
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


class PasswordResetView(APIView):
    """Запрос кода для сброса пароля — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.start_password_reset(serializer.validated_data['email'])
        except (services.CooldownError, services.RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({'detail': ENUMERATION_MSG})


class PasswordResetConfirmView(APIView):
    """Сброс пароля по коду из email."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_password_reset(
                serializer.validated_data['email'],
                serializer.validated_data['code'],
                serializer.validated_data['new_password'],
            )
        except services.CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({'detail': 'Пароль успешно изменён.'})


class MeView(RetrieveAPIView):
    """Профиль текущего пользователя."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
