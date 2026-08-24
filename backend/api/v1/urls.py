from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    CodeVerifyView,
    ExerciseViewSet,
    LoginCodeRequestView,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # djoser: регистрация, активация, сброс/смена пароля, профиль, JWT
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    # свой флоу одноразовых кодов: вход по коду
    path('auth/code/request/', LoginCodeRequestView.as_view()),
    path('auth/verify/', CodeVerifyView.as_view()),
]
