from django.contrib import admin

from .models import Assignment, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "course", "created_by", "due_date", "max_grade"]
    list_filter = ["course"]
    search_fields = ["title", "course__course_code"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["id", "assignment", "student", "status", "grade", "submitted_at"]
    list_filter = ["status", "assignment__course"]
    search_fields = ["student__user__college_id", "assignment__title"]
    readonly_fields = ["submitted_at", "graded_at"]
