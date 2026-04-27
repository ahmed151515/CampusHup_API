# No duplication — direct imports from attendances.permissions.
from attendances.permissions import (  # noqa: F401
    IsFacultyOfCourse,
    IsEnroll,
    IsFacultyOrAdmin,
    DenyAll,
)
