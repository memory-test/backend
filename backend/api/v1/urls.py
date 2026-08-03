from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views.exercises import (
    ExerciseTypeViewSet,
    ExerciseViewSet,
    PassExerciseView,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)
router.register('exercises/types', ExerciseTypeViewSet)

urlpatterns = [
    path(
        'pass_exercises/<int:exercise_id>/',
        PassExerciseView.as_view(),
        name='exercise-detail',
    ),
    path('', include(router.urls)),
]
