from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..permissions import CourseAccessPermission
from ..models import Course
from ..serializers import CourseSerializer, EnrollmentSerializer, CourseFacultySerializer


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
    permission_classes = [CourseAccessPermission]
    lookup_field = "course_code"

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.all().order_by("course_code")

        if not user.is_authenticated:
            return Course.objects.none()

        role = getattr(user, 'role', None)
        if role == 'admin':
            return qs
        elif role == 'faculty':
            if hasattr(user, 'faculty_profile'):
                return qs.filter(faculty_assignments__faculty=user.faculty_profile)
            return Course.objects.none()
        elif role == 'student':
            if hasattr(user, 'student_profile'):
                return qs.filter(enrollments__student=user.student_profile)
            return Course.objects.none()

        return Course.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        tags=["courses"],
        summary="Enroll a student in this course",
        description="Enroll a student into the course. Requires Admin permissions.",
        request=EnrollmentSerializer,
        responses={201: EnrollmentSerializer, 400: "Bad Request"},
    )
    @action(detail=True, methods=["post"], url_path="enroll")
    def enroll_student(self, request, course_code=None):
        course = self.get_object()
        serializer = EnrollmentSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.validated_data.get("student")
            if course.enrollments.filter(student=student).exists():
                return Response(
                    {"detail": "This student is already enrolled in this course."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save(course=course)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["courses"],
        summary="List all students enrolled in this course",
        responses={200: EnrollmentSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="enrollments")
    def list_enrollments(self, request, course_code=None):
        course = self.get_object()
        enrollments = course.enrollments.all()
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["courses"],
        summary="Assign a faculty member to this course",
        description="Assign a lecturer or assistant to the course. Requires Admin permissions.",
        request=CourseFacultySerializer,
        responses={201: CourseFacultySerializer, 400: "Bad Request"},
    )
    @action(detail=True, methods=["post"], url_path="assign-faculty")
    def assign_faculty(self, request, course_code=None):
        course = self.get_object()
        serializer = CourseFacultySerializer(data=request.data)
        if serializer.is_valid():
            faculty = serializer.validated_data.get("faculty")
            role = serializer.validated_data.get("role")

            # Check if this specific person is already assigned to this course
            if course.faculty_assignments.filter(faculty=faculty).exists():
                return Response(
                    {"detail": "This faculty member is already assigned to this course."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if this role is already filled by someone else
            if course.faculty_assignments.filter(role=role).exists():
                return Response(
                    {
                        "detail": f"A {role} is already assigned to this course. Each course can have at most one lecturer and one assistant."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save(course=course)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["courses"],
        summary="List all faculty assigned to this course",
        responses={200: CourseFacultySerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="faculty")
    def list_faculty(self, request, course_code=None):
        course = self.get_object()
        faculty = course.faculty_assignments.all()
        serializer = CourseFacultySerializer(faculty, many=True)
        return Response(serializer.data)
