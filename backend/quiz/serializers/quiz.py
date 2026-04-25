from rest_framework import serializers
from django.db import transaction
from quiz.models import Quiz, Question
from .question import QuestionSerializer, QuestionWriteSerializer


class QuizListSerializer(serializers.ModelSerializer):
    """Compact listing — shows question count instead of full nested list."""

    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "duration_minutes", "question_count"]


class QuizDetailSerializer(serializers.ModelSerializer):
    """Full detail — nested questions without correct_choice (student-safe)."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "duration_minutes", "questions"]


class QuizFacultyDetailSerializer(serializers.ModelSerializer):
    """Full detail — nested questions WITH correct_choice (faculty-safe)."""

    questions = QuestionWriteSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "duration_minutes", "questions"]


class QuizCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Writable serializer for faculty creating or updating a quiz.
    Accepts nested questions with correct_choice.
    """

    questions = QuestionWriteSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "duration_minutes", "questions"]
        read_only_fields = ["id"]

    def validate_questions(self, value):
        orders = [q.get("order") for q in value if q.get("order") is not None]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError("Questions must have unique order values.")
        return value

    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])
        with transaction.atomic():
            quiz = Quiz.objects.create(**validated_data)
            for q in questions_data:
                Question.objects.create(quiz=quiz, **q)
            return quiz

    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", None)
        with transaction.atomic():
            # Update scalar fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if questions_data is not None:
                # Replace all questions with the new set
                instance.questions.all().delete()
                for q in questions_data:
                    Question.objects.create(quiz=instance, **q)

            return instance

