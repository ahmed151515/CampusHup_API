from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


def assignment_upload_path(instance, filename: str) -> str:
    """Store assignment files under  assignments/<course_code>/<filename>."""
    return f"assignments/{instance.course_id}/{filename}"


def submission_upload_path(instance, filename: str) -> str:
    """Store submission files under  submissions/<course_code>/<assignment_id>/<filename>."""
    return f"submissions/{instance.assignment.course_id}/{instance.assignment_id}/{filename}"


class Assignment(models.Model):
    """An assignment created by a faculty member for a specific course."""

    id = models.BigAutoField(primary_key=True)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    created_by = models.ForeignKey(
        "accounts.FacultyProfile",
        on_delete=models.CASCADE,
        related_name="created_assignments",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)
    file = models.FileField(upload_to=assignment_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.course_id})"


class Submission(models.Model):
    """A student's submission for an assignment."""

    STATUS_PENDING = "pending"
    STATUS_GRADED = "graded"
    STATUS_LATE = "late"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_GRADED, "Graded"),
        (STATUS_LATE, "Late"),
    ]

    id = models.BigAutoField(primary_key=True)
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    file = models.FileField(upload_to=submission_upload_path)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    feedback = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        # Each student may submit only once per assignment.
        unique_together = ("assignment", "student")

    def clean(self) -> None:
        """Enforce grade ≤ max_grade business rule."""
        if (
            self.grade is not None
            and self.grade > self.assignment.max_grade
        ):
            raise ValidationError(
                {
                    "grade": (
                        f"Grade {self.grade} exceeds the maximum allowed "
                        f"grade of {self.assignment.max_grade}."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        """
        Auto-mark late submissions and set graded_at timestamp.
        Note: submitted_at is set by auto_now_add so we use timezone.now()
        for the late check on first save (pk is None).
        """
        is_new = self.pk is None

        if is_new:
            # Mark as late if submitted after the due date.
            if timezone.now() > self.assignment.due_date:
                self.status = self.STATUS_LATE

        # When grade is applied, record the timestamp and flip status.
        if self.grade is not None and self.status != self.STATUS_GRADED:
            self.status = self.STATUS_GRADED
            if self.graded_at is None:
                self.graded_at = timezone.now()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Submission by {self.student_id} for '{self.assignment}'"
