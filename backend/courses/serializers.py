from rest_framework import serializers
from .models import Course, Enrollment, CourseFaculty


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "course_code",
            "course_name",
            "description",
            "credit_hours",
            "department",
            "semester",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student", "student_name", "course", "status", "grade", "enrolled_at"]
        read_only_fields = ["id", "enrolled_at", "course"]


class CourseFacultySerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.user.get_full_name", read_only=True)

    class Meta:
        model = CourseFaculty
        fields = ["id", "faculty", "faculty_name", "course", "role", "assigned_at"]
        read_only_fields = ["id", "assigned_at", "course"]
