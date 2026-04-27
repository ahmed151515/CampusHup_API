from django.db import models


def material_upload_path(instance, filename: str) -> str:
    """Store PDFs under  materials/<course_code>/<filename>."""
    return f"materials/{instance.course_id}/{filename}"


def material_thumbnail_path(instance, filename: str) -> str:
    """Store thumbnails under  thumbnails/<course_code>/<filename>."""
    return f"thumbnails/{instance.course_id}/{filename}"


class Material(models.Model):
    """A PDF course material uploaded by a faculty member."""

    TYPE_PDF = "pdf"
    TYPE_CHOICES = [(TYPE_PDF, "PDF")]

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="materials",
    )
    uploaded_by = models.ForeignKey(
        "accounts.FacultyProfile",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_materials",
    )
    title = models.CharField(max_length=200)
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_PDF,
        editable=False,
    )
    file = models.FileField(upload_to=material_upload_path)
    thumbnail = models.ImageField(
        upload_to=material_thumbnail_path,
        null=True,
        blank=True,
    )
    size_bytes = models.BigIntegerField(default=0, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Material"
        verbose_name_plural = "Materials"

    def __str__(self) -> str:
        return f"{self.title} ({self.course_id})"
