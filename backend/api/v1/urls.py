from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    CodeVerifyView,
    ExerciseViewSet,
    HistoryDetailView,
    HistoryListView,
    LoginCodeRequestView,
)
from authentication.views import CodeUserViewSet

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)

user_router = DefaultRouter()
user_router.register('users', CodeUserViewSet, basename='user')

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
    path('auth/', include(user_router.urls)),
    path('auth/', include('djoser.urls.jwt')),
    path('auth/code/request/', LoginCodeRequestView.as_view()),
    path('auth/verify/', CodeVerifyView.as_view()),
]
