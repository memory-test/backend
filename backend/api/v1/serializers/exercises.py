from rest_framework import serializers

from exercises.models import Exercise, ExerciseType


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

# TODO: продумать что отдавать на фронт кроме атрибутов EvaluationResult
class ResultExerciseSerializer(serializers.Serializer):
    """Отдает результаты проверки задания"""
    pass

# TODO: Для каждого типа задания необходимо написать кастомный сериализатор
class ChoiceExerciseSerializer(serializers.Serializer):
    pass
