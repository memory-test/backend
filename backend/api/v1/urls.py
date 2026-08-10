from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    ExerciseTypeViewSet,
    ExerciseViewSet,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)
router.register('exercises/types', ExerciseTypeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
