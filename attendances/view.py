from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from .serializers import AttendanceSerializers, Attendance
from django.core.cache import cache
from .permissions import IsEnroll, IsFacultyOfCourse, DenyAll, IsFacultyOrAdmin
from rest_framework.response import Response
from rest_framework import status
from uuid import uuid4
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

# ---------------------------------------------------------------------------
# Reusable inline response schemas
# ---------------------------------------------------------------------------

_code_response_serializer = inline_serializer(
    name="AttendanceCodeResponse",
    fields={
        "code": drf_serializers.CharField(help_text="6-character alphanumeric session code"),
        "expires_in": drf_serializers.IntegerField(help_text="Seconds until the code expires (always 600)"),
    },
)

_detail_failed_serializer = inline_serializer(
    name="AttendanceFailedResponse",
    fields={"detail": drf_serializers.CharField(help_text='One of "failed" or "already_marked"')},
)

_partial_update_request_serializer = inline_serializer(
    name="PartialUpdateAttendanceRequest",
    fields={
        "is_present": drf_serializers.BooleanField(help_text="true = present, false = absent.")
    },
)


class AttendanceViewsets(viewsets.ViewSet):
    """
    Manages course attendance. Base URL: ``/api/v1/courses/{course_code}/attendances/``

    Permission matrix: ``list`` → IsFacultyOrAdmin | ``code/partial_update/destroy`` →
    IsFacultyOfCourse | ``create/me`` → IsEnroll | others → DenyAll.
    """

    serializer_class = AttendanceSerializers

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_queryset(self):
        """Return all Attendance records for the course in the URL."""
        return Attendance.objects.filter(course_id=self.course_code)

    def get_permissions(self):
        """Resolve permission classes for the current action."""
        permission_classes = [IsAuthenticated]
        match self.action:
            case "list":
                permission_classes += [IsFacultyOrAdmin]
            case "partial_update" | "destroy" | "code":
                permission_classes += [IsFacultyOfCourse]
            case "create" | "me":
                permission_classes += [IsEnroll]
            case _:
                permission_classes = [DenyAll]
        return [permission() for permission in permission_classes]

    @property
    def course_code(self):
        """Extract ``course_code`` from URL kwargs."""
        return self.kwargs.get("course_code", "")

    def generation_attendance_code(self):
        """Return a random 6-character hex session code."""
        return uuid4().__str__()[:6]

    # ------------------------------------------------------------------
    # Standard ViewSet actions
    # ------------------------------------------------------------------

    @extend_schema(
        summary="List all attendance records for a course",
        description="Returns every record for the course. **Access:** Faculty of the course or admin.",
        responses={
            200: AttendanceSerializers(many=True),
            403: OpenApiResponse(description="Forbidden – not faculty or admin."),
        },
        tags=["Attendance"],
    )
    def list(self, request, **kwargs):
        """Return all attendance records for the current course."""
        serializer = AttendanceSerializers(self.get_queryset(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Mark attendance using a session code",
        description=(
            "Enrolled student submits the 6-char faculty-generated code to be marked present. "
            "Returns ``failed`` (no/wrong code) or ``already_marked`` (duplicate) on error."
        ),
        parameters=[
            OpenApiParameter(
                name="course_code",
                location=OpenApiParameter.PATH,
                description="The unique course code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        request=inline_serializer(
            name="CreateAttendanceRequest",
            fields={
                "code": drf_serializers.CharField(
                    help_text="The 6-character session code displayed by the faculty."
                )
            },
        ),
        responses={
            201: AttendanceSerializers(),
            400: OpenApiResponse(
                description='``detail``: "failed" (invalid code) or "already_marked" (duplicate).',
                response=_detail_failed_serializer,
            ),
            403: OpenApiResponse(description="Forbidden – not an enrolled student."),
        },
        tags=["Attendance"],
        examples=[
            OpenApiExample(name="Valid code submission", value={"code": "a3f9c1"}, request_only=True),
            OpenApiExample(
                name="Already marked today",
                value={"detail": "already_marked"},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def create(self, request, **kwargs):
        """Mark the requesting student present using the active session code."""
        course_code = self.course_code

        session_code = cache.get(f"attendance_{course_code}", None)

        if not session_code:
            return Response({"detail": "failed"}, status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get("code", None)
        if not code:
            return Response({"detail": "failed"}, status=status.HTTP_400_BAD_REQUEST)

        if code != session_code:
            return Response({"detail": "failed"}, status=status.HTTP_400_BAD_REQUEST)

        attendance, created = Attendance.objects.get_or_create(
            course_id=course_code,
            student=request.user.profile,
            date=timezone.now().date(),
        )
        if not created:
            return Response(
                {"detail": "already_marked"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AttendanceSerializers(attendance)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Override a student's attendance status",
        description="Faculty manually sets ``is_present`` on a record. Only ``is_present`` is accepted.",
        parameters=[
            OpenApiParameter(
                name="course_code",
                location=OpenApiParameter.PATH,
                description="The unique course code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        request=_partial_update_request_serializer,
        responses={
            200: AttendanceSerializers(),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
            404: OpenApiResponse(description="No attendance record with the given pk."),
        },
        tags=["Attendance"],
    )
    def partial_update(self, request, **kwargs):
        """Update ``is_present`` on the attendance record identified by pk."""
        attendance = get_object_or_404(Attendance, pk=kwargs.get("pk", None))

        attendance.is_present = request.data.get("is_present")
        attendance.save()
        serializer = AttendanceSerializers(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @extend_schema(
        summary="Get or renew the session attendance code",
        description=(
            "Returns the active 6-char code for the course (TTL 600 s). "
            "Creates one on cache miss; resets TTL on cache hit. **Access:** Faculty only."
        ),
        parameters=[
            OpenApiParameter(
                name="course_code",
                location=OpenApiParameter.PATH,
                description="The unique course code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        responses={
            200: _code_response_serializer,
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
        },
        tags=["Attendance"],
        examples=[
            OpenApiExample(
                name="Successful code response",
                value={"code": "a3f9c1", "expires_in": 600},
                response_only=True,
                status_codes=["200"],
            )
        ],
    )
    @action(detail=False, methods=["get"])
    def code(self, request, **kwargs):
        """Return (or create) the active session code; reset its TTL each call."""
        course_code = self.course_code
        code = cache.get(f"attendance_{course_code}", None)

        if not code:
            code = self.generation_attendance_code()
            cache.set(f"attendance_{course_code}", code, 60 * 10)
        else:
            cache.touch(f"attendance_{course_code}", 60 * 10)

        return Response(
            data={"code": code, "expires_in": 60 * 10}, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Get the authenticated student's own attendance history",
        description="Returns only the current student's records for this course. **Access:** Enrolled students only.",
        parameters=[
            OpenApiParameter(
                name="course_code",
                location=OpenApiParameter.PATH,
                description="The unique course code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        responses={
            200: AttendanceSerializers(many=True),
            403: OpenApiResponse(description="Forbidden – not an enrolled student."),
        },
        tags=["Attendance"],
    )
    @action(detail=False, methods=["get"])
    def me(self, request, **kwargs):
        """Return the authenticated student's attendance records for this course."""
        attendances = self.get_queryset().filter(student=request.user.profile)
        serialize = AttendanceSerializers(attendances, many=True)
        return Response(serialize.data, status=status.HTTP_200_OK)
