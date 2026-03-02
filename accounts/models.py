from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Base user — handles login / auth for everyone."""

    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("admin",   "Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.username} ({self.role})"




class StudentProfile(models.Model):
    """Extra data that only a student has."""

    

    user            = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        limit_choices_to={"role": "student"},
    )

    department      = models.CharField(max_length=100, blank=True)
    join_date_year  = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="The calendar year the student enrolled, e.g. 2023",
    )
    gpa             = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        help_text="GPA on a 4.0 scale",
    )

    

    def __str__(self):
        return f"StudentProfile({self.user.username})"


class FacultyProfile(models.Model):
    """Extra data that only a faculty member has."""

    user           = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
        limit_choices_to={"role": "faculty"},
    )
    department     = models.CharField(max_length=100, blank=True)
    name          = models.CharField(max_length=100, blank=True)
    


    def __str__(self):
        return f"FacultyProfile({self.user.username})"



