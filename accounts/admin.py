from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, StudentProfile, FacultyProfile


# ── Base User ────────────────────────────────────────────────
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ["college_id"]  # ✅ replace username with college_id
    list_display = ["college_id", "email", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["college_id", "email"]


# ── Student Profile ──────────────────────────────────────────
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "department", "join_date_year", "gpa"]
    list_filter = ["department", "join_date_year"]
    search_fields = ["user__college_id", "user__email", "department"]
    fieldsets = (
        (None, {"fields": ("user",)}),
        ("Academic Info", {"fields": ("department", "join_date_year", "gpa")}),
    )


# ── Faculty Profile ──────────────────────────────────────────
@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "department"]
    list_filter = ["department"]
    search_fields = ["user__college_id", "user__email", "name", "department"]
    fieldsets = (
        (None, {"fields": ("user",)}),
        ("Faculty Info", {"fields": ("name", "department")}),
    )
