from django.contrib import admin

from .models import StudentProfile, FacultyProfile, Student, Faculty, Admin, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    ordering = ("name",)


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False

    fieldsets = [(None, {"fields": ["join_date_year"]})]


class FacultyProfileInline(admin.StackedInline):
    model = FacultyProfile
    can_delete = False


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    inlines = [StudentProfileInline]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "college_id",
                    "first_name",
                    "last_name",
                    "email",
                    "department",
                ]
            },
        )
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="student")


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    inlines = [FacultyProfileInline]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "college_id",
                    "first_name",
                    "last_name",
                    "email",
                    "department",
                ]
            },
        )
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="faculty")


@admin.register(Admin)
class AdminUserAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "college_id",
                    "first_name",
                    "last_name",
                    "email",
                    "department",
                ]
            },
        )
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="admin")
