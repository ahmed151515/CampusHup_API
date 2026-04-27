from decimal import Decimal
from rest_framework import serializers
from quiz.models import QuizSubmission, SubmissionAnswer


class SubmitAnswerSerializer(serializers.Serializer):
    """Input: one answer from a student — question id and chosen option."""

    question_id = serializers.IntegerField()
    selected_choice = serializers.IntegerField(min_value=1, max_value=4)


class QuizSubmitSerializer(serializers.Serializer):
    """Input: the full submission payload — a list of answers."""

    answers = SubmitAnswerSerializer(many=True)


class SubmissionAnswerSerializer(serializers.ModelSerializer):
    """Read: one answered question with correctness flag."""

    is_correct = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubmissionAnswer
        fields = ["question_id", "selected_choice", "is_correct"]


class QuizSubmissionSerializer(serializers.ModelSerializer):
    """Read: faculty view of a single student submission."""

    answers = SubmissionAnswerSerializer(many=True, read_only=True)
    student = serializers.StringRelatedField()

    class Meta:
        model = QuizSubmission
        fields = ["id", "student", "score", "started_at", "submitted_at", "answers"]


class MyGradeSerializer(serializers.ModelSerializer):
    """Read: student's own result with breakdown statistics."""

    total_questions = serializers.SerializerMethodField()
    correct_count = serializers.SerializerMethodField()
    total_marks = serializers.SerializerMethodField()

    class Meta:
        model = QuizSubmission
        fields = [
            "score",
            "submitted_at",
            "total_questions",
            "correct_count",
            "total_marks",
        ]

    def get_total_questions(self, obj) -> int:
        return obj.quiz.questions.count()

    def get_correct_count(self, obj) -> int:
        return sum(1 for a in obj.answers.select_related("question") if a.is_correct)

    def get_total_marks(self, obj) -> Decimal:
        return Decimal(
            sum(q.marks for q in obj.quiz.questions.all())
        )
