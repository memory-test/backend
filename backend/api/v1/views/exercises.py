from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from api.v1.filters import ExerciseFilter
from backend.api.v1.serializers import (
    ExerciseSerializer,
    ExerciseSessionSerializer,
    ExerciseTypeSerializer,
    ResultExerciseSerializer,
)
from exercises.models import ExerciseBase
from exercises.services import ChooseExerciseService
from progress.models import ExerciseSession, UserAnswer
from .registry import EXERCISE_REGISTRY


class ExerciseView(viewsets.ViewSet):
    """Контроллер для выполнения задания"""

    def _get_config(self, exercise_id: int) -> ExerciseConfig:
        """Вспомогательный метод для получения конфигурации по id задания."""
        exercise_type = get_object_or_404(
            ExerciseBase.objects.values('type'),
            id=exercise_id
        )['type']

        config = EXERCISE_REGISTRY.get(exercise_type)
        if not config:
            raise status.HTTP_400_BAD_REQUEST
        return config

    def list(self, request):
        queryset = ExerciseBase.objects.filter(is_active=True)
        serializer = ExerciseSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Отдает структуру задания.
        """
        config = self._get_config(pk)
        exercise = config.service.get_exercise(pk)
        serializer = config.serializer_class(exercise)
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
        serializer = config.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        clean_data = serializer.validated_data
        task_result = config.service.check_answer(
            exercise, clean_data.get('answer_data')
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
                success=task_result.get('success'),
                score=task_result.get('score'),
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


