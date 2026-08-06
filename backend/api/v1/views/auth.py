"""Эндпоинты авторизации.

Регистрация, запрос и подтверждение одноразового кода, восстановление
пароля, выдача JWT.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import (
    CodeRequestSerializer,
    CodeVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
)
from authentication import services

ENUMERATION_MSG = 'Если аккаунт существует, код отправлен на email.'

_REQUEST_CODE_HANDLERS = {
    services.REGISTRATION: services.resend_registration_code,
    services.LOGIN: services.request_login_code,
    services.PASSWORD_RESET: services.start_password_reset,
}

_VERIFY_CODE_HANDLERS = {
    services.REGISTRATION: services.confirm_registration,
    services.LOGIN: services.login_with_code,
}


class RegisterView(APIView):
    """Регистрация пользователя и отправка кода подтверждения."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except (services.CooldownError, services.RateLimitError) as exc:
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
        purpose = serializer.validated_data['purpose']
        handler = _REQUEST_CODE_HANDLERS[purpose]
        try:
            handler(serializer.validated_data['email'])
        except (services.CooldownError, services.RateLimitError) as exc:
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
        purpose = serializer.validated_data['purpose']
        handler = _VERIFY_CODE_HANDLERS[purpose]
        try:
            _, tokens = handler(
                serializer.validated_data['email'],
                serializer.validated_data['code'],
            )
        except services.CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(tokens)


class PasswordResetView(APIView):
    """Запрос кода для сброса пароля — анти-enumeration ответ."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.start_password_reset(serializer.validated_data['email'])
        except (services.CooldownError, services.RateLimitError) as exc:
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
            services.confirm_password_reset(
                serializer.validated_data['email'],
                serializer.validated_data['code'],
                serializer.validated_data['new_password'],
            )
        except services.CodeVerificationError as exc:
            return Response(
                {'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({'detail': 'Пароль успешно изменён.'})
