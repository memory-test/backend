from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.v1.filters import ExerciseFilter
from api.v1.serializers import (
    ExerciseSerializer,
    ExerciseSessionSerializer,
    ExerciseTypeSerializer,
)
from exercises.models import Exercise, ExerciseType
from exercises.services import check_answer
from progress.models import ExerciseSession, UserAnswer

# Вьюсеты приложения exercises неаписаны на readonly, т.к. на данный момент нет
# понимания будет ли админиистратор использовать фунционал api через фронт,
# либо только использовать панель администратора.


class ExerciseTypeViewSet(ReadOnlyModelViewSet):
    """Вьюсет для чтения объектов модели ExerciseType."""

    queryset = ExerciseType.objects.all()
    serializer_class = ExerciseTypeSerializer
    pagination_class = None


class ExerciseViewSet(ReadOnlyModelViewSet):
    """Вьюсет для чтения объектов модели Exercise."""

    queryset = Exercise.objects.select_related('type').filter(is_active=True)
    serializer_class = ExerciseSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = ExerciseFilter
    search_fields = ('title',)
    ordering_fields = ('title', 'type__name', 'difficulty', 'created_at')


class PassExerciseView(APIView):
    """/api/v1/exercises/<int:exercise_id>/."""

    # Данный эдпоинт по логике больше подходить для создания новых упражений.
    # Логичнее для проходения упражнений использовать:
    # */pass_exercises/<int:exercise_id>/ либо что-то с сессией связанное

    def post(self, request, exercise_id: int):
        """сохраняем ответы пользователя, нужно для статистики."""
        serializer = ExerciseSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data
        # сразу получим объект задания, чтобы избежать лишних запросов в бд.
        exercise = get_object_or_404(Exercise, id=exercise_id)
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
                exercise_id=exercise_id,
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


class PassedExerciseListView(APIView):
    """path /api/v1/exercises/ здесь будем обрабатывать этот эндпоинт."""

    # Эндпоинт занят списком доступных упражений.

    pass
