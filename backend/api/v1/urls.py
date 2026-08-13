from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from api.v1.views import ExerciseTypeViewSet, ExerciseViewSet
from api.v1.views.auth import (
    CodeRequestView,
    CodeVerifyView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
)
from api.v1.views.users import MeView

router = DefaultRouter()
router.register('exercises', ExerciseViewSet)
router.register('exercises/types', ExerciseTypeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view()),
    path('auth/code/request/', CodeRequestView.as_view()),
    path('auth/verify/', CodeVerifyView.as_view()),
    path('auth/password/reset/', PasswordResetView.as_view()),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view()),
    path('token/', TokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('users/me/', MeView.as_view()),
]
