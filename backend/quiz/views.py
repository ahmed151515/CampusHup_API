from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Quiz, QuizSubmission
from .permissions import IsFacultyOrAdmin, IsFacultyOfCourse, IsEnroll, DenyAll
from .serializers import (
    QuizListSerializer,
    QuizDetailSerializer,
    QuizFacultyDetailSerializer,
    QuizCreateUpdateSerializer,
    QuizSubmitSerializer,
    QuizSubmissionSerializer,
    MyGradeSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["quiz"],
        summary="List quizzes for a course",
    ),
    create=extend_schema(
        tags=["quiz"],
        summary="Create a quiz with nested questions",
    ),
    retrieve=extend_schema(
        tags=["quiz"],
        summary="Retrieve a quiz with its questions",
    ),
    update=extend_schema(
        tags=["quiz"],
        summary="Replace a quiz (blocked if submissions exist)",
    ),
    partial_update=extend_schema(
        tags=["quiz"],
        summary="Partially update a quiz (blocked if submissions exist)",
    ),
    destroy=extend_schema(
        tags=["quiz"],
        summary="Delete a quiz (blocked if submissions exist)",
    ),
)
class QuizViewSet(viewsets.ModelViewSet):
    """
    Quiz management for a course.

    Views are thin: authentication + permission checks + delegation to model methods.
    All business logic lives in QuizSubmission model methods.
    """

    def get_queryset(self):
        return (
            Quiz.objects.filter(course_id=self.kwargs["course_code"])
            .prefetch_related("questions")
            .select_related("created_by")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return QuizListSerializer
        if self.action in ("create", "update", "partial_update"):
            return QuizCreateUpdateSerializer
        if self.action == "retrieve":
            if getattr(self.request.user, "role", "") in ("faculty", "admin"):
                return QuizFacultyDetailSerializer
        return QuizDetailSerializer

    def get_permissions(self):
        match self.action:
            case "list" | "retrieve":
                perms = [IsAuthenticated, IsFacultyOrAdmin | IsEnroll]
            case "create" | "update" | "partial_update" | "destroy":
                perms = [IsAuthenticated, IsFacultyOfCourse]
            case "start" | "submit" | "my_grade":
                perms = [IsAuthenticated, IsEnroll]
            case "submissions":
                perms = [IsAuthenticated, IsFacultyOrAdmin]
            case _:
                perms = [DenyAll]
        return [p() for p in perms]

    def perform_create(self, serializer):
        serializer.save(
            course_id=self.kwargs["course_code"],
            created_by=self.request.user.faculty_profile,
        )

    def perform_update(self, serializer):
        if self.get_object().submissions.exists():
            raise ValidationError(
                {"detail": "Cannot edit a quiz that already has student submissions."}
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.submissions.exists():
            raise ValidationError(
                {"detail": "Cannot delete a quiz that already has student submissions."}
            )
        instance.delete()

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @extend_schema(tags=["quiz"], summary="Start a quiz (records start time)")
    @action(methods=["POST"], detail=True)
    def start(self, request, course_code, pk=None):
        """
        Student starts a quiz. Creates a QuizSubmission and records started_at.
        Idempotent — multiple calls return the same submission without error.
        """
        quiz = self.get_object()
        submission, _ = QuizSubmission.objects.get_or_create(
            quiz=quiz,
            student=request.user.student_profile,
        )
        try:
            submission.start()
        except DjangoValidationError as exc:
            raise ValidationError({"detail": exc.message})

        return Response(
            {"started_at": submission.started_at, "quiz_id": quiz.pk},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["quiz"],
        summary="Submit quiz answers (auto-graded, time-enforced)",
        request=QuizSubmitSerializer,
    )
    @action(methods=["POST"], detail=True)
    def submit(self, request, course_code, pk=None):
        """
        Student submits answers. Delegates all logic to QuizSubmission.submit().

        Handles edge cases:
        - Submit without calling /start/ first → auto-records started_at.
        - Already submitted → 400.
        - Time expired → 400.
        - Partial answers → accepted.
        """
        quiz = self.get_object()
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission, _ = QuizSubmission.objects.get_or_create(
            quiz=quiz,
            student=request.user.student_profile,
        )
        try:
            submission.submit(serializer.validated_data["answers"])
        except DjangoValidationError as exc:
            raise ValidationError({"detail": exc.message})

        return Response(
            {
                "score": submission.score,
                "submitted_at": submission.submitted_at,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(tags=["quiz"], summary="List all student submissions (faculty/admin)")
    @action(methods=["GET"], detail=True)
    def submissions(self, request, course_code, pk=None):
        """Faculty / admin views all submissions with scores for a quiz."""
        quiz = self.get_object()
        qs = quiz.submissions.select_related("student").prefetch_related(
            "answers__question"
        )
        serializer = QuizSubmissionSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["quiz"], summary="Get own grade (student)")
    @action(methods=["GET"], detail=True, url_path="my-grade")
    def my_grade(self, request, course_code, pk=None):
        """Student retrieves their own submission and grade breakdown."""
        quiz = self.get_object()
        try:
            submission = QuizSubmission.objects.prefetch_related(
                "answers__question"
            ).get(quiz=quiz, student=request.user.student_profile)
        except QuizSubmission.DoesNotExist:
            raise NotFound("You have not submitted this quiz yet.")

        if submission.submitted_at is None:
            raise NotFound("You have not submitted this quiz yet.")

        serializer = MyGradeSerializer(submission)
        return Response(serializer.data)
