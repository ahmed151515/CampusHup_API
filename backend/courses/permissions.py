from rest_framework.permissions import BasePermission

class CourseAccessPermission(BasePermission):
    """
    Custom permission for courses:
    - Admin can access all endpoints
    - Students can ONLY GET /api/v1/courses/{course_code}/ if they are enrolled
    - Faculty and others have read-only access (GET, HEAD, OPTIONS)
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(request.user, 'role', None)

        # Admins have full access
        if role == 'admin':
            return True

        # Students can access list and retrieve actions
        if role == 'student':
            return view.action in ['list', 'retrieve']

        # Faculty can access list and retrieve
        if role == 'faculty':
            return view.action in ['list', 'retrieve']

        return False

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, 'role', None)
        if role == 'admin':
            return True

        if role == 'student':
            if view.action == 'retrieve':
                if hasattr(request.user, 'student_profile'):
                    return obj.enrollments.filter(student=request.user.student_profile).exists()
            return False

        if role == 'faculty':
            if view.action == 'retrieve':
                if hasattr(request.user, 'faculty_profile'):
                    return obj.faculty_assignments.filter(faculty=request.user.faculty_profile).exists()
            return False

        return False
