from rest_framework import viewsets

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from accounts.permissions import IsAdminOrReadOnly
from ..models import Department
from ..serializers import DepartmentSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all departments",
        description="Returns all departments ordered by name. **Access:** Any authenticated user.",
        responses={200: DepartmentSerializer(many=True)},
        tags=["Departments"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a department",
        description="Returns a single department by its unique ``code``. **Access:** Any authenticated user.",
        parameters=[
            OpenApiParameter(
                name="code",
                location=OpenApiParameter.PATH,
                description="The unique department code (e.g. ``CS``).",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        responses={
            200: DepartmentSerializer(),
            404: OpenApiResponse(description="No department with the given code."),
        },
        tags=["Departments"],
    ),
    create=extend_schema(
        summary="Create a department",
        description="Creates a new department. **Access:** Admin only.",
        request=DepartmentSerializer,
        responses={
            201: DepartmentSerializer(),
            400: OpenApiResponse(description="Validation error – missing or duplicate fields."),
            403: OpenApiResponse(description="Forbidden – admin role required."),
        },
        tags=["Departments"],
    ),
    update=extend_schema(
        summary="Replace a department",
        description="Full update of a department record. **Access:** Admin only.",
        parameters=[
            OpenApiParameter(
                name="code",
                location=OpenApiParameter.PATH,
                description="The unique department code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        request=DepartmentSerializer,
        responses={
            200: DepartmentSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden – admin role required."),
            404: OpenApiResponse(description="No department with the given code."),
        },
        tags=["Departments"],
    ),
    partial_update=extend_schema(
        summary="Partially update a department",
        description="Updates one or more fields of a department. **Access:** Admin only.",
        parameters=[
            OpenApiParameter(
                name="code",
                location=OpenApiParameter.PATH,
                description="The unique department code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        request=DepartmentSerializer,
        responses={
            200: DepartmentSerializer(),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden – admin role required."),
            404: OpenApiResponse(description="No department with the given code."),
        },
        tags=["Departments"],
    ),
    destroy=extend_schema(
        summary="Delete a department",
        description="Permanently deletes a department. **Access:** Admin only.",
        parameters=[
            OpenApiParameter(
                name="code",
                location=OpenApiParameter.PATH,
                description="The unique department code.",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        responses={
            204: OpenApiResponse(description="Department deleted successfully."),
            403: OpenApiResponse(description="Forbidden – admin role required."),
            404: OpenApiResponse(description="No department with the given code."),
        },
        tags=["Departments"],
    ),
)
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Department records. Base URL: ``/api/v1/departments/``

    **Permission:** Read (list/retrieve) → any authenticated user. Write (create/update/delete) → admin only.
    Lookup field is ``code`` (the department's primary key), not ``id``.
    """

    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "code"
