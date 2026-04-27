from django.contrib import admin
from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "uploaded_by", "type", "size_bytes", "uploaded_at")
    list_filter = ("course", "type")
    search_fields = ("title", "course__course_code", "uploaded_by__user__college_id")
    readonly_fields = ("type", "size_bytes", "uploaded_at", "thumbnail")
