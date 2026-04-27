"""
Permissions for the contents app.

IsFacultyOfCourse  – faculty assigned to this course (write operations)
IsEnroll           – student enrolled in this course (read operations)

Both reuse the same logic as attendances.permissions so the same
permission classes are kept in sync without duplication.
"""

from attendances.permissions import IsFacultyOfCourse, IsEnroll  # noqa: F401

__all__ = ["IsFacultyOfCourse", "IsEnroll"]
