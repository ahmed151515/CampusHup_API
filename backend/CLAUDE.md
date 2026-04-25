# CampusHup API — Agent Instructions

## Project Stack
- Django 6 + Django REST Framework
- drf-spectacular (Swagger/OpenAPI docs)
- SimpleJWT for authentication
- pytest + pytest-django for tests

---

## Conventions Every Agent Must Follow

### 1. Swagger Tags — REQUIRED on every endpoint

Every view/viewset **must** have a `drf-spectacular` tag so it appears in the correct group in the Swagger UI.

**For ViewSets** — use `@extend_schema_view` on the class:

```python
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(tags=["<app_name>"]),
    create=extend_schema(tags=["<app_name>"]),
    retrieve=extend_schema(tags=["<app_name>"]),
    update=extend_schema(tags=["<app_name>"]),
    partial_update=extend_schema(tags=["<app_name>"]),
    destroy=extend_schema(tags=["<app_name>"]),
)
class MyViewSet(viewsets.ModelViewSet):
    ...
```

**For individual APIViews / third-party views wired in urls.py** — apply inline:

```python
from drf_spectacular.utils import extend_schema

path(
    "auth/login/",
    extend_schema(tags=["auth"])(TokenObtainPairView).as_view(),
    name="token_obtain_pair",
),
```

**Tag naming rules:**
- Use the Django **app name** as the tag (e.g., `"courses"`, `"accounts"`, `"attendances"`)
- Auth-related views use `"auth"`
- Always lowercase, always a list: `tags=["courses"]`

---

### 2. Permissions

- Read-only endpoints for any authenticated user → `IsAdminOrReadOnly`
- Admin-only write endpoints → `IsAdmin`
- Custom per-app logic → create a `permissions.py` inside the app

---

### 3. Tests — required for every new endpoint

- Use `APITestCase` from DRF
- Reuse helpers from `accounts/tests.py`: `auth_header`, `get_list_data`, `make_admin`, `make_department`, `make_student`, `make_faculty`
- One assertion per test method
- Name format: `test_<action>_<scenario>_<expected>`
- Cover all roles: admin, faculty, student, unauthenticated
- Standard HTTP checks: 200, 201, 204, 400, 401, 403, 404

---

### 4. URL structure

```
/api/v1/accounts/      → accounts app
/api/v1/courses/       → courses app
/api/v1/auth/          → JWT auth (login, refresh, logout)
/api/v1/<course_code>/attendance/ → attendances app
/api/v1/<course_code>/quiz/       → quiz app
```

---

### 5. User model

- Primary key is `college_id` (not `id`)
- Roles: `"student"`, `"faculty"`, `"admin"`
- Always use `User.objects.create_student(...)`, `create_faculty(...)`, `create_admin(...)` — not `User.objects.create(...)`
