from exercises.models import Exercise, ExerciseType
from rest_framework import serializers


class ExerciseTypeSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса ExerciseType."""

    class Meta:
        model = ExerciseType
        fields = '__all__'


class ExerciseSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Exercise."""

    type = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Exercise
        fields = '__all__'
