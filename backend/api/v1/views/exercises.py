from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.api.v1.serializers.progress import ExerciseSerializer
from backend.exercises.models import Exercise
from backend.exercises.services import check_answer
from backend.progress.models import ExerciseSession, UserAnswer


class ExerciseDetailView(APIView):
    """/api/v1/exercises/<int:exercise_id>/"""

    def post(self, request, exercise_id: int):
        """сохраняем ответы пользователя, нужно для статистики"""
        serializer = ExerciseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data
        # сразу получим объект задания, чтобы избежать лишних запросов в бд.
        exercise = get_object_or_404(Exercise, id=exercise_id)
        task_result: dict = check_answer(
            exercise, clean_data.get('answer_data')
        )
        # здесь получаем количество попыток пользователя до этой сессии.
        sessions_count: int = ExerciseSession.objects.filter(
            user=request.user,
            exercise_id=exercise
        ).count() + 1

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
                attempts_count=sessions_count
            )
            UserAnswer.objects.create(
                session=session,
                answer_data=clean_data.get('answer_data'),
                is_correct=task_result.get('is_correct'),
                response_time=float(clean_data.get('duration_seconds'))
            )

        return Response(
            {
                "status": "success",
                "session_id": session.id,
                "score": session.score,
                "success": session.success,
                "attempts_count": session.attempts_count
            },
            status=status.HTTP_201_CREATED
        )






class ExerciseListView(APIView):
    """path /api/v1/exercises/ здесь будем обрабатывать этот эндпоинт"""

    pass


