from django.contrib import admin
from .models import Course, CourseFaculty, Enrollment, Timetable


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_code",
        "course_name",
        "department",
        "semester",
        "credit_hours",
        "is_active",
    )
    list_filter = ("department", "semester", "is_active")
    search_fields = ("course_code", "course_name")
    ordering = ("course_code",)


@admin.register(CourseFaculty)
class CourseFacultyAdmin(admin.ModelAdmin):
    list_display = ("course", "faculty", "role", "assigned_at")
    list_filter = ("role",)
    search_fields = (
        "course__course_code",
        "course__course_name",
        "faculty__user__first_name",
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "grade", "enrolled_at")
    list_filter = ("status",)
    search_fields = ("student__college_id", "course__course_code")


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "faculty",
        "day_of_week",
        "start_time",
        "end_time",
        "room",
        "semester",
    )
    list_filter = ("day_of_week", "semester")
    search_fields = ("course__course_code", "room")
