from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import Course
from ..serializers import CourseSerializer


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve courses.

    * GET /api/v1/courses/         → list all active courses
    * GET /api/v1/courses/{id}/    → retrieve a single course
    """

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(is_active=True).order_by("course_code")
