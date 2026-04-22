from django.db import models

# Create your models here.


class Attendance(models.Model):
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.PROTECT,
        limit_choices_to={"role": "student"},
        related_name="attendance",
    )

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="attendance",
        to_field="course_code",
    )

    date = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now=True)

    is_present = models.BooleanField(default=True)

    class Meta:
        unique_together = ["student", "course", "date"]
