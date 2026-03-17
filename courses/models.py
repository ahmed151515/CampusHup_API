from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import FacultyProfile, User
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'admin'},
        related_name='created_courses'
    )
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    credit_hours = models.PositiveIntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    semester = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(14)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

class CourseFaculty(models.Model):
    ROLE_CHOICES = [
        ('lecturer', 'Lecturer'),
        ('assistant', 'Assistant'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faculty_assignments')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='course_assignments')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'faculty')
        verbose_name_plural = 'Course faculty'

    def __str__(self):
        return f"{self.faculty} - {self.course} ({self.role})"

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
    ]
    student = models.ForeignKey(User, limit_choices_to={"role": "student"}, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    grade = models.CharField(max_length=5, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"

class Timetable(models.Model):
    DAYS_OF_WEEK = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='timetables')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='timetables')
    day_of_week = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50)
    semester = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.course} schedule on {self.day_of_week}"
