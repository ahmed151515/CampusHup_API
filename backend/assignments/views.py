from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.models import Enrollment

from .models import Assignment, Submission
from .permissions import IsAssignedFaculty, IsEnrolledStudent, IsSubmissionOwner
from .serializers import (
    AssignmentSerializer,
    AssignmentWriteSerializer,
    GradeSubmissionSerializer,
    SubmissionCreateSerializer,
    SubmissionSerializer,
)

# ---------------------------------------------------------------------------
# Shared OpenAPI path parameter
# ---------------------------------------------------------------------------

_COURSE_CODE_PARAM = OpenApiParameter(
    name="course_code",
    location=OpenApiParameter.PATH,
    description="The unique code of the course (e.g. CS301).",
    required=True,
    type=OpenApiTypes.STR,
)

# Swagger multipart schemas that render a real file-picker widget.
_ASSIGNMENT_UPLOAD_SCHEMA = {
    "multipart/form-data": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 200},
            "description": {"type": "string"},
            "due_date": {"type": "string", "format": "date-time"},
            "max_grade": {"type": "number"},
            "file": {"type": "string", "format": "binary"},
        },
        "required": ["title", "description", "due_date", "max_grade"],
    }
}

_SUBMISSION_UPLOAD_SCHEMA = {
    "multipart/form-data": {
        "type": "object",
        "properties": {
            "file": {"type": "string", "format": "binary"},
        },
        "required": ["file"],
    }
}


# ---------------------------------------------------------------------------
# AssignmentViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="List course assignments",
        description=(
            "Returns all assignments for the course. "
            "**Access:** Enrolled students or faculty assigned to this course."
        ),
        parameters=[_COURSE_CODE_PARAM],
        responses={
            200: AssignmentSerializer(many=True),
            403: OpenApiResponse(description="Forbidden."),
        },
        tags=["Assignments"],
    ),
    retrieve=extend_schema(
        summary="Retrieve an assignment",
        description=(
            "Returns a single assignment. "
            "**Access:** Enrolled students or faculty assigned to this course."
        ),
        parameters=[_COURSE_CODE_PARAM],
        responses={
            200: AssignmentSerializer(),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Assignment not found."),
        },
        tags=["Assignments"],
    ),
    create=extend_schema(
        summary="Create an assignment",
        description=(
            "Create a new assignment for this course. "
            "**Access:** Faculty assigned to this course only."
        ),
        parameters=[_COURSE_CODE_PARAM],
        request=_ASSIGNMENT_UPLOAD_SCHEMA,
        responses={
            201: AssignmentSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
        },
        tags=["Assignments"],
    ),
    update=extend_schema(
        summary="Update an assignment (full)",
        description="Full replacement of the assignment. **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        request=_ASSIGNMENT_UPLOAD_SCHEMA,
        responses={
            200: AssignmentSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not found."),
        },
        tags=["Assignments"],
    ),
    partial_update=extend_schema(
        summary="Partially update an assignment",
        description="Update one or more fields. **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        request=_ASSIGNMENT_UPLOAD_SCHEMA,
        responses={
            200: AssignmentSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not found."),
        },
        tags=["Assignments"],
    ),
    destroy=extend_schema(
        summary="Delete an assignment",
        description="Permanently deletes the assignment and all its submissions. **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not found."),
        },
        tags=["Assignments"],
    ),
)
class AssignmentViewSet(viewsets.ModelViewSet):
    """
    CRUD for course assignments.

    Permission matrix
    -----------------
    list / retrieve    → IsAuthenticated + (IsEnrolledStudent | IsAssignedFaculty)
    create / update
    / partial_update
    / destroy          → IsAuthenticated + IsAssignedFaculty
    """

    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "pk"

    # ------------------------------------------------------------------
    # Queryset
    # ------------------------------------------------------------------

    def get_queryset(self):
        return (
            Assignment.objects.filter(course_id=self.kwargs["course_code"])
            .select_related("course", "created_by")
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # Serializer selection
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AssignmentWriteSerializer
        return AssignmentSerializer

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            # Both enrolled students and course faculty can read
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAssignedFaculty()]

    def check_read_permission(self, request, obj=None):
        """
        For read actions, allow if the user is either an enrolled student
        or a faculty assigned to the course.
        """
        user = request.user
        role = getattr(user, "role", None)
        course_code = self.kwargs["course_code"]

        if role == "student" and hasattr(user, "student_profile"):
            return Enrollment.objects.filter(
                student=user.student_profile,
                course_id=course_code,
                status="active",
            ).exists()

        if role == "faculty" and hasattr(user, "faculty_profile"):
            from courses.models import CourseFaculty
            return CourseFaculty.objects.filter(
                course_id=course_code,
                faculty=user.faculty_profile,
            ).exists()

        return False

    def list(self, request, *args, **kwargs):
        if not self.check_read_permission(request):
            return Response(
                {"detail": "You are not enrolled in or assigned to this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not self.check_read_permission(request):
            return Response(
                {"detail": "You are not enrolled in or assigned to this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Save helpers
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        serializer.save(
            course_id=self.kwargs["course_code"],
            created_by=self.request.user.faculty_profile,
        )

    def get_object(self):
        obj = super().get_object()
        # For write actions enforce object-level faculty check.
        if self.action not in ("list", "retrieve"):
            perm = IsAssignedFaculty()
            if not perm.has_object_permission(self.request, self, obj):
                self.permission_denied(
                    self.request, message=perm.message
                )
        return obj


# ---------------------------------------------------------------------------
# SubmissionViewSet  (nested under an assignment)
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="List submissions",
        description=(
            "Students see only their own submission. "
            "Faculty see all submissions for this assignment. "
            "**Access:** Enrolled students or faculty of the course."
        ),
        parameters=[_COURSE_CODE_PARAM],
        responses={200: SubmissionSerializer(many=True)},
        tags=["Submissions"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a submission",
        parameters=[_COURSE_CODE_PARAM],
        responses={
            200: SubmissionSerializer(),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not found."),
        },
        tags=["Submissions"],
    ),
    create=extend_schema(
        summary="Submit an assignment",
        description=(
            "Upload a file as a submission for this assignment. "
            "Submitting after the due date marks the submission as **late**. "
            "Each student may submit only once. "
            "**Access:** Enrolled students only."
        ),
        parameters=[_COURSE_CODE_PARAM],
        request=_SUBMISSION_UPLOAD_SCHEMA,
        responses={
            201: SubmissionSerializer(),
            400: OpenApiResponse(description="Validation error (already submitted, etc.)."),
            403: OpenApiResponse(description="Forbidden – not an enrolled student."),
        },
        tags=["Submissions"],
    ),
    grade=extend_schema(
        summary="Grade a submission",
        description=(
            "Set a grade (and optional feedback) for a submission. "
            "Grade must not exceed the assignment's max_grade. "
            "**Access:** Faculty assigned to this course only."
        ),
        parameters=[_COURSE_CODE_PARAM],
        request=GradeSubmissionSerializer,
        responses={
            200: SubmissionSerializer(),
            400: OpenApiResponse(description="Grade exceeds max_grade."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not found."),
        },
        tags=["Submissions"],
        methods=["PATCH"],
    ),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    """
    Manage submissions for a specific assignment.

    Permission matrix
    -----------------
    list / retrieve  → student (own only) or faculty (all)
    create           → enrolled student only (once per assignment)
    grade (PATCH)    → faculty of the course only
    update / delete  → disabled (submissions are immutable)
    """

    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "pk"
    http_method_names = ["get", "post", "patch", "head", "options"]

    # ------------------------------------------------------------------
    # Queryset
    # ------------------------------------------------------------------

    def get_queryset(self):
        assignment_pk = self.kwargs["assignment_pk"]
        user = self.request.user
        role = getattr(user, "role", None)

        qs = Submission.objects.filter(
            assignment_id=assignment_pk
        ).select_related("assignment", "student")

        # Students only see their own submissions.
        if role == "student" and hasattr(user, "student_profile"):
            qs = qs.filter(student=user.student_profile)

        return qs.order_by("-submitted_at")

    # ------------------------------------------------------------------
    # Serializer selection
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == "create":
            return SubmissionCreateSerializer
        if self.action == "grade":
            return GradeSubmissionSerializer
        return SubmissionSerializer

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action == "create":
            return [IsAuthenticated(), IsEnrolledStudent()]
        if self.action == "grade":
            return [IsAuthenticated(), IsAssignedFaculty()]
        # Disable update / delete
        return [IsAuthenticated(), IsAssignedFaculty()]

    def _get_assignment(self):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(
            Assignment, pk=self.kwargs["assignment_pk"]
        )

    # ------------------------------------------------------------------
    # Create (student submit)
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        assignment = self._get_assignment()
        student_profile = self.request.user.student_profile

        # Enforce enrollment in the assignment's course.
        if not Enrollment.objects.filter(
            student=student_profile,
            course_id=assignment.course_id,
            status="active",
        ).exists():
            raise drf_serializers.ValidationError(
                "You are not enrolled in this course."
            )

        serializer.save(
            assignment=assignment,
            student=student_profile,
        )

    # ------------------------------------------------------------------
    # Grade action (faculty only)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["patch"], url_path="grade")
    def grade(self, request, *args, **kwargs):
        submission = self.get_object()

        # Object-level faculty check.
        perm = IsAssignedFaculty()
        if not perm.has_object_permission(request, self, submission):
            return Response(
                {"detail": perm.message},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GradeSubmissionSerializer(
            submission, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            SubmissionSerializer(submission).data,
            status=status.HTTP_200_OK,
        )
