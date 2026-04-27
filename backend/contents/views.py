from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from .models import Material
from .permissions import IsFacultyOfCourse, IsEnroll
from .serializers import MaterialSerializer

_COURSE_CODE_PARAM = OpenApiParameter(
    name="course_code",
    location=OpenApiParameter.PATH,
    description="The unique code of the course (e.g. CS301).",
    required=True,
    type=OpenApiTypes.STR,
)

_UPLOAD_REQUEST_SCHEMA = {
    "multipart/form-data": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 200},
            "file": {"type": "string", "format": "binary"},
        },
        "required": ["title", "file"],
    }
}


@extend_schema_view(
    list=extend_schema(
        summary="List course materials",
        description="Returns all PDF materials for the course. **Access:** Enrolled students only.",
        parameters=[_COURSE_CODE_PARAM],
        responses={
            200: MaterialSerializer(many=True),
            403: OpenApiResponse(description="Forbidden – not an enrolled student."),
        },
        tags=["Contents"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a single material",
        description="Returns a single PDF material. **Access:** Enrolled students only.",
        parameters=[_COURSE_CODE_PARAM],
        responses={
            200: MaterialSerializer(),
            403: OpenApiResponse(description="Forbidden – not an enrolled student."),
            404: OpenApiResponse(description="Material not found."),
        },
        tags=["Contents"],
    ),
    create=extend_schema(
        summary="Upload a PDF material",
        description=(
            "Upload a new PDF material for the course. "
            "Only PDF files are accepted (validated by extension and MIME type). "
            "A thumbnail is generated automatically from the first page. "
            "**Access:** Faculty assigned to this course only."
        ),
        parameters=[_COURSE_CODE_PARAM],
        request=_UPLOAD_REQUEST_SCHEMA,
        responses={
            201: MaterialSerializer(),
            400: OpenApiResponse(description="Validation error (non-PDF, oversized, corrupted, etc.)."),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
        },
        tags=["Contents"],
    ),
    update=extend_schema(
        summary="Replace a material (full update)",
        description="Full replacement of the material record. File re-validation is applied. **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        request=_UPLOAD_REQUEST_SCHEMA,
        responses={
            200: MaterialSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
            404: OpenApiResponse(description="Material not found."),
        },
        tags=["Contents"],
    ),
    partial_update=extend_schema(
        summary="Partially update a material",
        description="Update one or more fields. If a new file is provided it is re-validated. **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        request=_UPLOAD_REQUEST_SCHEMA,
        responses={
            200: MaterialSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
            404: OpenApiResponse(description="Material not found."),
        },
        tags=["Contents"],
    ),
    destroy=extend_schema(
        summary="Delete a material",
        description="Permanently deletes the material (and its stored file on S3). **Access:** Faculty of this course.",
        parameters=[_COURSE_CODE_PARAM],
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            403: OpenApiResponse(description="Forbidden – not faculty of this course."),
            404: OpenApiResponse(description="Material not found."),
        },
        tags=["Contents"],
    ),
)
class MaterialViewSet(viewsets.ModelViewSet):
    """
    CRUD for course PDF materials.

    Permission matrix
    -----------------
    list / retrieve  → IsAuthenticated + IsEnroll
    create           → IsAuthenticated + IsFacultyOfCourse
    update / partial_update / destroy → IsAuthenticated + IsFacultyOfCourse
    """

    serializer_class = MaterialSerializer
    lookup_field = "pk"
    parser_classes = [MultiPartParser, FormParser]

    # ------------------------------------------------------------------
    # Queryset
    # ------------------------------------------------------------------

    def get_queryset(self):
        """Return only materials that belong to the course in the URL."""
        return (
            Material.objects.filter(course_id=self.kwargs["course_code"])
            .select_related("uploaded_by", "course")
            .order_by("-uploaded_at")
        )

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def get_permissions(self):
        """
        Read actions → enrolled students.
        Write actions → faculty of the course.
        """
        if self.action in ("list", "retrieve"):
            permission_classes = [IsAuthenticated, IsEnroll]
        else:
            permission_classes = [IsAuthenticated, IsFacultyOfCourse]
        return [perm() for perm in permission_classes]

    # ------------------------------------------------------------------
    # Save helpers
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        """Inject the uploader (FacultyProfile) and course from the URL."""
        course_code = self.kwargs["course_code"]
        serializer.save(
            uploaded_by=self.request.user.faculty_profile,
            course_id=course_code,
        )
