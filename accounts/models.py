from __future__ import annotations
from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, primary_key=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("admin", "Admin"),
    ]

    username = None  # removed — using college_id instead

    college_id = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="College ID",
        help_text="Student: 202603001 | Faculty: DR001 | Admin: ADMIN01",
        primary_key=True,
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="student",
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="users"
    )

    objects = UserManager()

    USERNAME_FIELD = "college_id"
    REQUIRED_FIELDS = []

    @property
    def profile(self) -> StudentProfile | FacultyProfile:
        if self.role == "student":
            return self.student_profile
        elif self.role == "faculty":
            return self.faculty_profile
        raise AttributeError(
            f"User '{self.college_id}' has role '{self.role}' — no profile"
        )

    def __str__(self):
        return f"{self.college_id} ({self.role})"


class StudentProfile(models.Model):
    """Extra data that only a student has."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        limit_choices_to={"role": "student"},
    )

    join_date_year = models.PositiveSmallIntegerField(
        help_text="The calendar year the student enrolled, e.g. 2023",
    )
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="GPA on a 4.0 scale",
        default=0.00,
    )

    def __str__(self):
        return f"StudentProfile({self.user.college_id})"


class FacultyProfile(models.Model):
    """Extra data that only a faculty member has."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
        limit_choices_to={"role": "faculty"},
    )

    def __str__(self):
        return f"FacultyProfile({self.user.college_id})"


class Student(User):
    class Meta:
        proxy = True
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="student")


class Faculty(User):
    class Meta:
        proxy = True
        verbose_name = "Faculty"
        verbose_name_plural = "Faculty"

    def save(self, *args, **kwargs):
        self.role = "faculty"
        self.set_password(self.college_id)
        super().save(*args, **kwargs)


class Admin(User):
    class Meta:
        proxy = True
        verbose_name = "Admin"
        verbose_name_plural = "Admins"

    def save(self, *args, **kwargs):
        self.role = "admin"
        self.set_password(self.college_id)
        self.is_staff = True
        self.department_id = "05"
        super().save(*args, **kwargs)
