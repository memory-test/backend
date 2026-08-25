from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    CodeVerifyView,
    ExerciseViewSet,
    HistoryDetailView,
    HistoryListView,
    LoginCodeRequestView,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path(
        'progress/history/',
        HistoryListView.as_view(),
        name='history-list',
    ),
    path(
        'progress/history/<int:pk>/',
        HistoryDetailView.as_view(),
        name='history-detail',
    ),
    # djoser: регистрация, активация, сброс/смена пароля, профиль, JWT
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    # свой флоу одноразовых кодов: вход по коду
    path('auth/code/request/', LoginCodeRequestView.as_view()),
    path('auth/verify/', CodeVerifyView.as_view()),
]
