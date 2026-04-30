from rest_framework import serializers

from .models import Assignment, Submission


# ---------------------------------------------------------------------------
# Assignment serializers
# ---------------------------------------------------------------------------

class AssignmentSerializer(serializers.ModelSerializer):
    """
    Full read serializer for Assignment.
    Exposed to enrolled students and faculty.
    """

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "created_by",
            "title",
            "description",
            "due_date",
            "max_grade",
            "file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course", "created_by", "created_at", "updated_at"]


class AssignmentWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating / updating an Assignment.
    course and created_by are injected by the view, not sent by the client.
    """

    class Meta:
        model = Assignment
        fields = [
            "title",
            "description",
            "due_date",
            "max_grade",
            "file",
        ]

    def validate_max_grade(self, value):
        if value <= 0:
            raise serializers.ValidationError("max_grade must be a positive number.")
        return value


# ---------------------------------------------------------------------------
# Submission serializers
# ---------------------------------------------------------------------------

class SubmissionSerializer(serializers.ModelSerializer):
    """
    Full read serializer for Submission.
    Students see their own; faculty see all for their course assignments.
    """

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "student",
            "file",
            "submitted_at",
            "grade",
            "feedback",
            "status",
            "graded_at",
        ]
        read_only_fields = [
            "id",
            "assignment",
            "student",
            "submitted_at",
            "grade",
            "feedback",
            "status",
            "graded_at",
        ]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for a student creating a new submission.
    assignment and student are injected by the view.
    """

    class Meta:
        model = Submission
        fields = ["file"]


class GradeSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for faculty to grade a submission.
    Only grade and feedback are writable; status / graded_at are managed in model.save().
    """

    class Meta:
        model = Submission
        fields = ["grade", "feedback"]

    def validate_grade(self, value):
        """Validate that grade does not exceed max_grade."""
        assignment = self.instance.assignment if self.instance else None
        if assignment and value is not None and value > assignment.max_grade:
            raise serializers.ValidationError(
                f"Grade {value} exceeds max_grade of {assignment.max_grade}."
            )
        return value
