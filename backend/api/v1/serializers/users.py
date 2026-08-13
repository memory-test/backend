from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Профиль пользователя."""

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'name',
            'birth_date',
            'current_difficulty',
            'role',
            'is_active',
            'created_at',
        )
        read_only_fields = fields
