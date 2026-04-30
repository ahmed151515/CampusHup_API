from rest_framework.permissions import BasePermission

from courses.models import CourseFaculty, Enrollment


class IsAssignedFaculty(BasePermission):
    """
    Allow access only to faculty members who are assigned to the course
    that owns the assignment.

    Works for both Assignment-level views (course_code in URL kwargs) and
    Submission-grading views (assignment pk in URL kwargs — resolved via
    the view's get_object() assignment reference).
    """

    message = "Only faculty assigned to this course can perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(user, "role", None) == "faculty"

    def has_object_permission(self, request, view, obj) -> bool:
        """obj is an Assignment or a Submission instance."""
        user = request.user
        if not hasattr(user, "faculty_profile"):
            return False

        # Resolve the course from the object.
        if hasattr(obj, "course_id"):
            course_id = obj.course_id          # Assignment
        elif hasattr(obj, "assignment"):
            course_id = obj.assignment.course_id  # Submission
        else:
            return False

        return CourseFaculty.objects.filter(
            course_id=course_id,
            faculty=user.faculty_profile,
        ).exists()


class IsEnrolledStudent(BasePermission):
    """
    Allow access only to students who are actively enrolled in the course
    that owns the assignment.

    Enrollment status must be 'active'.
    """

    message = "Only students enrolled in this course can access this resource."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(user, "role", None) == "student"

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not hasattr(user, "student_profile"):
            return False

        if hasattr(obj, "course_id"):
            course_id = obj.course_id
        elif hasattr(obj, "assignment"):
            course_id = obj.assignment.course_id
        else:
            return False

        return Enrollment.objects.filter(
            student=user.student_profile,
            course_id=course_id,
            status="active",
        ).exists()


class IsSubmissionOwner(BasePermission):
    """
    Allow a student to access only their own submissions.
    Combined with IsEnrolledStudent for full permission checks.
    """

    message = "You can only access your own submissions."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not hasattr(user, "student_profile"):
            return False
        return obj.student == user.student_profile
