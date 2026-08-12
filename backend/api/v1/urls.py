from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views.exercises import (
    ExerciseTypeViewSet,
    ExerciseViewSet,
)
from api.v1.views.progress import (
    HistoryListView,
    HistoryDetailView,
    StartExerciseView,
    SubmitAnswerView,
    FinishExerciseView,
    RetryExerciseView,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)
router.register('exercises/types', ExerciseTypeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path(
        'progress/history/',
        HistoryListView.as_view(),
        name='history-list'
    ),
    path(
        'progress/history/<int:id>/',
        HistoryDetailView.as_view(),
        name='history-detail'
    ),
    path(
        'progress/exercises/<int:exercise_id>/start/',
        StartExerciseView.as_view(),
        name='exercise-start'
    ),
    path(
        'progress/sessions/<int:session_id>/submit/',
        SubmitAnswerView.as_view(),
        name='submit-answer'
    ),
    path(
        'progress/sessions/<int:session_id>/finish/',
        FinishExerciseView.as_view(),
        name='exercise-finish'
    ),
    path(
        'progress/exercises/<int:exercise_id>/retry/',
        RetryExerciseView.as_view(),
        name='exercise-retry'
    ),
]
