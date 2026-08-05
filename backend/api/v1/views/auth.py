from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from api.v1.serializers import (
    CodeRequestSerializer,
    CodeVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
)
from authentication.services import (
    PASSWORD_RESET,
    REGISTRATION,
    CodeVerificationError,
    CooldownError,
    RateLimitError,
    request_code,
    reset_password,
    verify_code,
)
from users.models import User

ENUMERATION_MSG = 'Если аккаунт существует, код отправлен на email.'


def issue_tokens(user):
    """Возвращает пару JWT (access, refresh) для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class RegisterView(APIView):
    """Регистрация пользователя и отправка кода подтверждения."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except (CooldownError, RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response(
            {
                'detail': 'Код подтверждения отправлен на email.',
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class CodeRequestView(APIView):
    """Запрос кода (регистрация/вход/сброс) — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_code(
                serializer.validated_data['email'],
                serializer.validated_data['purpose'],
            )
        except (CooldownError, RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({'detail': ENUMERATION_MSG})


class CodeVerifyView(APIView):
    """Подтверждение кода (регистрация/вход) с выдачей JWT."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CodeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        purpose = serializer.validated_data['purpose']
        try:
            verify_code(email, code, purpose)
        except CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.get(email=email)
        if purpose == REGISTRATION and not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
        return Response(issue_tokens(user))


class PasswordResetView(APIView):
    """Запрос кода для сброса пароля — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_code(serializer.validated_data['email'], PASSWORD_RESET)
        except (CooldownError, RateLimitError) as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({'detail': ENUMERATION_MSG})


class PasswordResetConfirmView(APIView):
    """Сброс пароля по коду из email."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password(
                serializer.validated_data['email'],
                serializer.validated_data['code'],
                serializer.validated_data['new_password'],
            )
        except CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({'detail': 'Пароль успешно изменён.'})
