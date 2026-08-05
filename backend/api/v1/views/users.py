from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from api.v1.serializers import UserSerializer


class MeView(RetrieveAPIView):
    """Профиль текущего пользователя."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
