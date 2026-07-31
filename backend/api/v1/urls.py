from django.urls import path
from views.exercises import ExerciseDetailView

urlpatterns = [
    path(
'exercises/<int:exercise_id>/',
        ExerciseDetailView.as_view(),
        name='exercise-detail'
    ),
]
