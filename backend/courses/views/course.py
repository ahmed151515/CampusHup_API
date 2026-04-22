from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrReadOnly
from ..models import Course
from ..serializers import CourseSerializer


@extend_schema_view(
    list=extend_schema(tags=["courses"]),
    create=extend_schema(tags=["courses"]),
    retrieve=extend_schema(tags=["courses"]),
    update=extend_schema(tags=["courses"]),
    partial_update=extend_schema(tags=["courses"]),
    destroy=extend_schema(tags=["courses"]),
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for courses.

    * GET /api/v1/courses/         → list all active courses
    * POST /api/v1/courses/        → create a new course
    * GET /api/v1/courses/{id}/    → retrieve a single course
    * PUT/PATCH /api/v1/courses/{id}/ → update a course
    * DELETE /api/v1/courses/{id}/ → delete a course
    """

    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "course_code"

    def get_queryset(self):
        return Course.objects.all().order_by("course_code")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
