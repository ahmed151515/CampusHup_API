from __future__ import annotations
from django.contrib.auth.base_user import BaseUserManager


# fields that belong to User model
USER_FIELDS = {"college_id", "first_name", "last_name", "email"}

# fields that belong to StudentProfile
STUDENT_FIELDS = {"department", "join_date_year", "gpa"}

# fields that belong to FacultyProfile
FACULTY_FIELDS = {"department", "name"}


class UserManager(BaseUserManager):
    def create_user(self, college_id, role, **extra) -> User:  # noqa: F821
        if not college_id:
            raise ValueError("College ID is required")

        user = self.model(college_id=college_id, role=role, **extra)
        user.set_password(college_id)
        user.save(using=self._db)
        return user

    def create_student(self, data: dict):
        from .models import StudentProfile

        # split data into user fields and profile fields
        user_data = {k: v for k, v in data.items() if k in USER_FIELDS}
        profile_data = {k: v for k, v in data.items() if k in STUDENT_FIELDS}

        user = self.create_user(role="student", **user_data)

        StudentProfile.objects.create(user=user, **profile_data)
        return user

    def create_faculty(self, data: dict):
        from .models import FacultyProfile

        user_data = {k: v for k, v in data.items() if k in USER_FIELDS}
        profile_data = {k: v for k, v in data.items() if k in FACULTY_FIELDS}

        user = self.create_user(role="faculty", **user_data)

        FacultyProfile.objects.create(user=user, **profile_data)
        return user

    def create_superuser(self, college_id, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)

        user = self.model(college_id=college_id, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
