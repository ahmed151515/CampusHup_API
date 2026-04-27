from __future__ import annotations
from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction

# # fields that belong to User model
# USER_FIELDS = {"college_id", "first_name", "last_name", "email"}

# # fields that belong to StudentProfile
# STUDENT_FIELDS = {"department", "join_date_year", "gpa"}

# # fields that belong to FacultyProfile
# FACULTY_FIELDS = {"department", "name"}


class UserManager(BaseUserManager):
    def create_user(self, role, **extra) -> User:  # noqa: F821
        if not extra["college_id"]:
            raise ValueError("College ID is required")

        user = self.model(role=role, **extra)
        user.set_password(extra["college_id"])
        user.save(using=self._db)
        return user

    def create_student(self, data: dict) -> User:  # noqa: F821
        from .models import StudentProfile

        profile_data = data.pop(
            "student_profile",
        )
        user_data = data

        with transaction.atomic():
            user = self.create_user(role="student", **user_data)

            StudentProfile.objects.create(user=user, **profile_data)
        return user

    def create_faculty(self, data: dict) -> User:  # noqa: F821
        from .models import FacultyProfile

        profile_data = data.pop("faculty_profile", {})
        user_data = data
        with transaction.atomic():
            user = self.create_user(role="faculty", **user_data)

            FacultyProfile.objects.create(user=user, **profile_data)
        return user

    def create_superuser(self, college_id, password=None, **extra):

        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("department_id", "05")

        user = self.model(college_id=college_id, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_admin(self, data: dict) -> User:  # noqa: F821
        data.setdefault("is_staff", True)
        data.setdefault("is_superuser", False)
        data.setdefault("department_id", "05")

        with transaction.atomic():
            user = self.create_user(role="admin", **data)
        return user
