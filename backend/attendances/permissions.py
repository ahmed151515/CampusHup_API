from rest_framework import permissions
from courses.models import CourseFaculty, Enrollment
from accounts.permissions import IsAdmin


class IsFacultyOfCourse(permissions.BasePermission):
    def has_permission(self, request, view):
        course_code = view.kwargs.get("course_code", "")

        return (
            request.user.role == "faculty"
            and CourseFaculty.objects.filter(
                course_id=course_code, faculty_id=request.user.college_id
            ).exists()
        )


class IsEnroll(permissions.BasePermission):
    def has_permission(self, request, view):
        course_code = view.kwargs.get("course_code", "")
        return (
            request.user.role == "student"
            and Enrollment.objects.filter(
                course_id=course_code, student_id=request.user.college_id
            ).exists()
        )


class DenyAll(permissions.BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):

        return False


class IsFacultyOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):

        return IsAdmin().has_permission(
            request, view
        ) or IsFacultyOfCourse().has_permission(request, view)
