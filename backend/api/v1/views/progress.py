from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from progress.models import ExerciseSession, UserAnswer
from api.v1.serializers.progress import (
    HistoryListSerializer,
    HistoryDetailSerializer,
    StartExerciseSerializer,
    SubmitAnswerSerializer,
    FinishExerciseSerializer,
)
from exercises.models import Exercise


class StartExerciseView(views.APIView):
    """
    POST /api/progress/exercises/<exercise_id>/start/
    Начало прохождения задания (создание сессии).
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, exercise_id):
        serializer = StartExerciseSerializer(data={'exercise_id': exercise_id})
        serializer.is_valid(raise_exception=True)

        exercise = get_object_or_404(
            Exercise,
            id=exercise_id,
            is_active=True
        )

        open_session = ExerciseSession.objects.filter(
            user=request.user,
            exercise=exercise,
            finished_at__isnull=True
        ).first()

        if open_session:
            history_serializer = HistoryDetailSerializer(open_session)
            return Response({
                'session_id': open_session.id,
                'message': 'Продолжаем существующую сессию',
                'is_new': False,
                'data': history_serializer.data
            }, status=status.HTTP_200_OK)

        config = exercise.config
        questions = config.get('questions', [])

        if not questions:
            return Response({
                'error': 'В задании нет вопросов'
            }, status=status.HTTP_400_BAD_REQUEST)

        new_session = ExerciseSession.objects.create(
            user=request.user,
            exercise=exercise,
            difficulty=exercise.difficulty,
            started_at=timezone.now(),
            finished_at=None,
            duration_seconds=0,
            success=False,
            score=0,
            attempts_count=0,
        )

        answers_to_create = []
        for idx, question_data in enumerate(questions):
            answers_to_create.append(
                UserAnswer(
                    session=new_session,
                    answer_data={
                        'question_id': idx,
                        'question_text': question_data.get('text', ''),
                        'question_type': question_data.get('type', 'choice'),
                        'correct_answer': question_data.get('correct'),
                        'options': question_data.get('options', []),
                        'user_answer': None,
                    },
                    is_correct=False,
                    response_time=0,
                )
            )

        UserAnswer.objects.bulk_create(answers_to_create)

        return Response({
            'session_id': new_session.id,
            'total_questions': len(questions),
            'message': 'Новая сессия начата',
            'is_new': True,
            'started_at': new_session.started_at,
        }, status=status.HTTP_201_CREATED)


class SubmitAnswerView(views.APIView):
    """
    POST /api/progress/sessions/<session_id>/submit/
    Отправка ответа на вопрос.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, session_id):
        session = get_object_or_404(
            ExerciseSession,
            id=session_id,
            user=request.user,
            finished_at__isnull=True
        )

        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        user_answer = serializer.validated_data['answer']
        response_time = serializer.validated_data['response_time']

        try:
            answer = UserAnswer.objects.get(
                session=session,
                answer_data__question_id=question_id
            )
        except UserAnswer.DoesNotExist:
            return Response({
                'error': 'Вопрос не найден в этой сессии'
            }, status=status.HTTP_404_NOT_FOUND)

        if answer.answer_data.get('user_answer') is not None:
            return Response({
                'error': 'На этот вопрос уже дан ответ',
                'question_id': question_id,
            }, status=status.HTTP_400_BAD_REQUEST)

        correct_answer = answer.answer_data.get('correct_answer')
        is_correct = self.check_answer(correct_answer, user_answer)

        answer.answer_data['user_answer'] = user_answer
        answer.is_correct = is_correct
        answer.response_time = response_time
        answer.save()

        correct_count = session.answers.filter(is_correct=True).count()
        total_count = session.answers.count()
        session.score = (
            correct_count / total_count * 100
        ) if total_count > 0 else 0
        session.attempts_count += 1
        session.save()

        return Response({
            'session_id': session.id,
            'question_id': question_id,
            'is_correct': is_correct,
            'current_score': session.score,
            'correct_count': correct_count,
            'total_questions': total_count,
        })

    def check_answer(self, correct, user_answer):
        """Универсальная проверка ответа."""
        if correct is None:
            return False

        if isinstance(correct, list) and isinstance(user_answer, list):
            return sorted(correct) == sorted(user_answer)

        if isinstance(correct, (int, float)) and isinstance(
            user_answer,
            (int, float)
        ):
            return abs(float(correct) - float(user_answer)) < 0.001

        if isinstance(correct, str) and isinstance(user_answer, str):
            return correct.strip().lower() == user_answer.strip().lower()

        if isinstance(correct, bool) and isinstance(user_answer, bool):
            return correct == user_answer

        return correct == user_answer


class FinishExerciseView(views.APIView):
    """
    POST /api/progress/sessions/<session_id>/finish/
    Завершение сессии.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, session_id):
        session = get_object_or_404(
            ExerciseSession,
            id=session_id,
            user=request.user,
            finished_at__isnull=True
        )

        serializer = FinishExerciseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unanswered = session.answers.filter(
            answer_data__user_answer__isnull=True
        ).count()

        if unanswered > 0:
            return Response({
                'error': f'Осталось {unanswered} неотвеченных вопросов',
                'unanswered_count': unanswered,
                'total_questions': session.answers.count(),
            }, status=status.HTTP_400_BAD_REQUEST)

        session.finished_at = timezone.now()
        session.duration_seconds = int(
            (session.finished_at - session.started_at).total_seconds()
        )
        session.success = session.score >= 70
        session.save()

        return Response({
            'session_id': session.id,
            'score': session.score,
            'success': session.success,
            'duration_seconds': session.duration_seconds,
            'finished_at': session.finished_at,
            'message': 'Сессия завершена',
        })


class HistoryListView(generics.ListAPIView):
    """История прохождения. Список завершенных упражнений."""
    serializer_class = HistoryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExerciseSession.objects.filter(
            user=self.request.user,
            finished_at__isnull=False
        ).select_related('exercise', 'exercise__type').order_by('-finished_at')


class HistoryDetailView(generics.RetrieveAPIView):
    """История прохождения. Детальный просмотр ответов."""
    serializer_class = HistoryDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExerciseSession.objects.filter(
            user=self.request.user
        ).prefetch_related('answers')

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            self.permission_denied(self.request)
        return obj


class RetryExerciseView(views.APIView):
    """
    POST /api/progress/exercises/<exercise_id>/retry/
    Перепрохождение упражнения (упрощенный вариант).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, exercise_id):
        view = StartExerciseView()
        return view.post(request, exercise_id)
