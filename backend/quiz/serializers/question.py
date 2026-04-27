from rest_framework import serializers
from quiz.models import Question


class QuestionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for students.
    Deliberately excludes `correct_choice` to prevent answer leaking.
    """

    class Meta:
        model = Question
        fields = ["id", "text", "order", "marks", "choice_1", "choice_2", "choice_3", "choice_4"]


class QuestionWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer used by faculty when creating / updating a quiz.
    Includes `correct_choice` because only faculty/admin can write.
    """

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "order",
            "marks",
            "choice_1",
            "choice_2",
            "choice_3",
            "choice_4",
            "correct_choice",
        ]
