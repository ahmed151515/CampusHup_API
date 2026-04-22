"""
Tests for the accounts app.

Endpoints covered
-----------------
Students (IsAdmin required):
    GET    /api/v1/accounts/students/                – list
    POST   /api/v1/accounts/students/                – create
    GET    /api/v1/accounts/students/{college_id}/   – retrieve
    PUT    /api/v1/accounts/students/{college_id}/   – full update
    PATCH  /api/v1/accounts/students/{college_id}/   – partial update
    DELETE /api/v1/accounts/students/{college_id}/   – soft-delete (deactivate)

Faculty (IsAdmin required):
    GET    /api/v1/accounts/faculty/                 – list
    POST   /api/v1/accounts/faculty/                 – create
    GET    /api/v1/accounts/faculty/{college_id}/    – retrieve
    PUT    /api/v1/accounts/faculty/{college_id}/    – full update
    PATCH  /api/v1/accounts/faculty/{college_id}/    – partial update
    DELETE /api/v1/accounts/faculty/{college_id}/    – soft-delete (deactivate)

Me (IsAuthenticated required):
    GET    /api/v1/accounts/me/                      – current user profile
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Department, User


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def get_tokens_for_user(user: User) -> dict:
    """Return a dict with 'access' and 'refresh' JWT strings for *user*."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def auth_header(user: User) -> dict:
    """Return an Authorization header dict ready to be passed to the client."""
    token = get_tokens_for_user(user)["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def get_list_data(response) -> list:
    """Return the list of items from a response, handling both paginated
    (dict with 'results' key) and non-paginated (plain list) responses."""
    data = response.data
    if isinstance(data, dict):
        return data.get("results", data)
    return data  # plain list (no pagination)


def make_department(
    code: str = "CS", name: str = "Computer Science"
) -> Department:
    """Return a Department, creating it if it does not already exist."""
    dept, _ = Department.objects.get_or_create(code=code, defaults={"name": name})
    return dept


def make_admin(college_id: str = "ADMIN01") -> User:
    """Create and return an admin user.

    The manager hard-codes ``department_id='05'``, so we ensure that
    Department exists before creating the admin.
    """
    make_department(code="05", name="Administration")
    return User.objects.create_admin(
        {
            "college_id": college_id,
            "first_name": "Admin",
            "last_name": "User",
            "email": f"{college_id.lower()}@test.com",
        }
    )


def make_student(college_id: str = "202601001") -> User:
    """Create a student user with a matching StudentProfile."""
    dept = make_department()
    return User.objects.create_student(
        {
            "college_id": college_id,
            "first_name": "John",
            "last_name": "Doe",
            "email": f"{college_id}@student.test.com",
            "department_id": dept.code,
            "student_profile": {
                "join_date_year": 2024,
            },
        }
    )


def make_faculty(college_id: str = "DR001") -> User:
    """Create a faculty user with a matching FacultyProfile."""
    dept = make_department()
    return User.objects.create_faculty(
        {
            "college_id": college_id,
            "first_name": "Jane",
            "last_name": "Smith",
            "email": f"{college_id.lower()}@faculty.test.com",
            "department_id": dept.code,
            "faculty_profile": {},
        }
    )


# ---------------------------------------------------------------------------
# Student endpoints
# ---------------------------------------------------------------------------


class StudentListCreateTests(APITestCase):
    """Tests for GET/POST /api/v1/accounts/students/"""

    list_url = reverse("v1:student-list")

    # department is set in setUp so the FK exists before any request
    VALID_PAYLOAD = {
        "college_id": "202699001",
        "first_name": "Alice",
        "last_name": "Wonder",
        "email": "alice@student.test.com",
        "student_profile": {
            "join_date_year": 2025,
        },
    }

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.student = make_student()
        self.faculty = make_faculty()
        # Inject the real department PK so the view can resolve the FK
        self.VALID_PAYLOAD = {
            **self.__class__.VALID_PAYLOAD,
            "department": self.dept.code,
        }

    # ---- list ----

    def test_list_students_as_admin_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_students_contains_active_student(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        college_ids = [s["college_id"] for s in get_list_data(response)]
        self.assertIn(self.student.college_id, college_ids)

    def test_list_students_excludes_inactive_student(self):
        self.student.is_active = False
        self.student.save()
        response = self.client.get(self.list_url, **auth_header(self.admin))
        college_ids = [s["college_id"] for s in get_list_data(response)]
        self.assertNotIn(self.student.college_id, college_ids)

    def test_list_students_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_students_as_student_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_students_as_faculty_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- create ----

    def test_create_student_as_admin_returns_201(self):
        response = self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_student_persists_in_db(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        self.assertTrue(
            User.objects.filter(college_id=self.VALID_PAYLOAD["college_id"]).exists()
        )

    def test_create_student_creates_student_profile(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        user = User.objects.get(college_id=self.VALID_PAYLOAD["college_id"])
        self.assertTrue(hasattr(user, "student_profile"))

    def test_create_student_sets_role_to_student(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        user = User.objects.get(college_id=self.VALID_PAYLOAD["college_id"])
        self.assertEqual(user.role, "student")

    def test_create_student_duplicate_college_id_returns_400(self):
        payload = self.VALID_PAYLOAD.copy()
        payload["college_id"] = self.student.college_id  # already exists
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_student_missing_required_field_returns_400(self):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "email"}
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_student_unauthenticated_returns_401(self):
        response = self.client.post(self.list_url, self.VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_student_as_non_admin_returns_403(self):
        response = self.client.post(
            self.list_url,
            self.VALID_PAYLOAD,
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class StudentDetailTests(APITestCase):
    """Tests for GET/PUT/PATCH/DELETE /api/v1/accounts/students/{college_id}/"""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.student = make_student()
        self.faculty = make_faculty()
        self.detail_url = reverse(
            "v1:student-detail", kwargs={"college_id": self.student.college_id}
        )

    # ---- retrieve ----

    def test_retrieve_student_as_admin_returns_200(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_student_response_contains_expected_fields(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        for field in (
            "college_id",
            "first_name",
            "last_name",
            "email",
            "student_profile",
        ):
            self.assertIn(field, response.data)

    def test_retrieve_student_unauthenticated_returns_401(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_student_as_student_returns_403(self):
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_student_returns_404(self):
        url = reverse("v1:student-detail", kwargs={"college_id": "NOTEXIST"})
        response = self.client.get(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- full update (PUT) ----

    def test_full_update_student_as_admin_returns_200(self):
        payload = {
            "college_id": self.student.college_id,
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@student.test.com",
            "department": self.dept.code,
            "student_profile": {
                "join_date_year": 2023,
            },
        }
        response = self.client.put(
            self.detail_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_full_update_student_persists_changes(self):
        payload = {
            "college_id": self.student.college_id,
            "first_name": "Changed",
            "last_name": "Last",
            "email": "changed@student.test.com",
            "department": self.dept.code,
            "student_profile": {
                "join_date_year": 2022,
            },
        }
        self.client.put(
            self.detail_url, payload, format="json", **auth_header(self.admin)
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Changed")

    def test_full_update_student_unauthenticated_returns_401(self):
        response = self.client.put(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_full_update_student_as_non_admin_returns_403(self):
        response = self.client.put(
            self.detail_url, {}, format="json", **auth_header(self.student)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- partial update (PATCH) ----

    def test_partial_update_student_first_name(self):
        response = self.client.patch(
            self.detail_url,
            {"first_name": "Patched"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Patched")

    def test_partial_update_student_profile_join_date_year(self):
        """PATCH student_profile to update the join_date_year field."""
        response = self.client.patch(
            self.detail_url,
            {"student_profile": {"join_date_year": 2026}},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.student_profile.refresh_from_db()
        self.assertEqual(self.student.student_profile.join_date_year, 2026)

    def test_partial_update_student_unauthenticated_returns_401(self):
        response = self.client.patch(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_student_as_non_admin_returns_403(self):
        response = self.client.patch(
            self.detail_url, {}, format="json", **auth_header(self.faculty)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- soft-delete (DELETE) ----

    def test_delete_student_as_admin_returns_204(self):
        response = self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_student_sets_is_active_false(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_delete_student_does_not_remove_db_row(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertTrue(User.objects.filter(pk=self.student.pk).exists())

    def test_delete_student_removes_from_active_list(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        response = self.client.get(
            reverse("v1:student-list"), **auth_header(self.admin)
        )
        college_ids = [s["college_id"] for s in get_list_data(response)]
        self.assertNotIn(self.student.college_id, college_ids)

    def test_delete_student_unauthenticated_returns_401(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_student_as_non_admin_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_student_returns_404(self):
        url = reverse("v1:student-detail", kwargs={"college_id": "NOTEXIST"})
        response = self.client.delete(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Faculty endpoints
# ---------------------------------------------------------------------------


class FacultyListCreateTests(APITestCase):
    """Tests for GET/POST /api/v1/accounts/faculty/"""

    list_url = reverse("v1:faculty-list")

    # department is set in setUp so the FK exists before any request
    VALID_PAYLOAD = {
        "college_id": "DR999",
        "first_name": "Bob",
        "last_name": "Prof",
        "email": "bob.prof@faculty.test.com",
        "faculty_profile": {},
    }

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.student = make_student()
        self.faculty = make_faculty()
        self.VALID_PAYLOAD = {
            **self.__class__.VALID_PAYLOAD,
            "department": self.dept.code,
        }

    # ---- list ----

    def test_list_faculty_as_admin_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_faculty_contains_active_faculty(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        college_ids = [f["college_id"] for f in get_list_data(response)]
        self.assertIn(self.faculty.college_id, college_ids)

    def test_list_faculty_excludes_inactive_faculty(self):
        self.faculty.is_active = False
        self.faculty.save()
        response = self.client.get(self.list_url, **auth_header(self.admin))
        college_ids = [f["college_id"] for f in get_list_data(response)]
        self.assertNotIn(self.faculty.college_id, college_ids)

    def test_list_faculty_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_faculty_as_student_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_faculty_as_faculty_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- create ----

    def test_create_faculty_as_admin_returns_201(self):
        response = self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_faculty_persists_in_db(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        self.assertTrue(
            User.objects.filter(college_id=self.VALID_PAYLOAD["college_id"]).exists()
        )

    def test_create_faculty_creates_faculty_profile(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        user = User.objects.get(college_id=self.VALID_PAYLOAD["college_id"])
        self.assertTrue(hasattr(user, "faculty_profile"))

    def test_create_faculty_sets_role_to_faculty(self):
        self.client.post(
            self.list_url, self.VALID_PAYLOAD, format="json", **auth_header(self.admin)
        )
        user = User.objects.get(college_id=self.VALID_PAYLOAD["college_id"])
        self.assertEqual(user.role, "faculty")

    def test_create_faculty_duplicate_college_id_returns_400(self):
        payload = self.VALID_PAYLOAD.copy()
        payload["college_id"] = self.faculty.college_id
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_faculty_missing_required_field_returns_400(self):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "email"}
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_faculty_unauthenticated_returns_401(self):
        response = self.client.post(self.list_url, self.VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_faculty_as_non_admin_returns_403(self):
        response = self.client.post(
            self.list_url,
            self.VALID_PAYLOAD,
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FacultyDetailTests(APITestCase):
    """Tests for GET/PUT/PATCH/DELETE /api/v1/accounts/faculty/{college_id}/"""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.student = make_student()
        self.faculty = make_faculty()
        self.detail_url = reverse(
            "v1:faculty-detail", kwargs={"college_id": self.faculty.college_id}
        )

    # ---- retrieve ----

    def test_retrieve_faculty_as_admin_returns_200(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_faculty_response_contains_expected_fields(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        for field in (
            "college_id",
            "first_name",
            "last_name",
            "email",
            "faculty_profile",
        ):
            self.assertIn(field, response.data)

    def test_retrieve_faculty_unauthenticated_returns_401(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_faculty_as_student_returns_403(self):
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_faculty_returns_404(self):
        url = reverse("v1:faculty-detail", kwargs={"college_id": "NOTEXIST"})
        response = self.client.get(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- full update (PUT) ----

    def test_full_update_faculty_as_admin_returns_200(self):
        payload = {
            "college_id": self.faculty.college_id,
            "first_name": "Updated",
            "last_name": "Faculty",
            "email": "updated.faculty@test.com",
            "department": self.dept.code,
            "faculty_profile": {},
        }
        response = self.client.put(
            self.detail_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_full_update_faculty_persists_changes(self):
        payload = {
            "college_id": self.faculty.college_id,
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "email": "new@faculty.test.com",
            "department": self.dept.code,
            "faculty_profile": {},
        }
        self.client.put(
            self.detail_url, payload, format="json", **auth_header(self.admin)
        )
        self.faculty.refresh_from_db()
        self.assertEqual(self.faculty.first_name, "NewFirst")

    def test_full_update_faculty_unauthenticated_returns_401(self):
        response = self.client.put(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_full_update_faculty_as_non_admin_returns_403(self):
        response = self.client.put(
            self.detail_url, {}, format="json", **auth_header(self.faculty)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- partial update (PATCH) ----

    def test_partial_update_faculty_first_name(self):
        response = self.client.patch(
            self.detail_url,
            {"first_name": "Patched"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.faculty.refresh_from_db()
        self.assertEqual(self.faculty.first_name, "Patched")

    def test_partial_update_faculty_profile_empty_patch(self):
        """PATCH with an empty faculty_profile body should still return 200."""
        response = self.client.patch(
            self.detail_url,
            {"faculty_profile": {}},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_faculty_unauthenticated_returns_401(self):
        response = self.client.patch(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_faculty_as_non_admin_returns_403(self):
        response = self.client.patch(
            self.detail_url, {}, format="json", **auth_header(self.student)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- soft-delete (DELETE) ----

    def test_delete_faculty_as_admin_returns_204(self):
        response = self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_faculty_sets_is_active_false(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        self.faculty.refresh_from_db()
        self.assertFalse(self.faculty.is_active)

    def test_delete_faculty_does_not_remove_db_row(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertTrue(User.objects.filter(pk=self.faculty.pk).exists())

    def test_delete_faculty_removes_from_active_list(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        response = self.client.get(
            reverse("v1:faculty-list"), **auth_header(self.admin)
        )
        college_ids = [f["college_id"] for f in get_list_data(response)]
        self.assertNotIn(self.faculty.college_id, college_ids)

    def test_delete_faculty_unauthenticated_returns_401(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_faculty_as_non_admin_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_faculty_returns_404(self):
        url = reverse("v1:faculty-detail", kwargs={"college_id": "NOTEXIST"})
        response = self.client.delete(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Me endpoint
# ---------------------------------------------------------------------------


class MeEndpointTests(APITestCase):
    """Tests for GET /api/v1/accounts/me/"""

    me_url = reverse("v1:me")

    def setUp(self):
        self.admin = make_admin()
        self.student = make_student()
        self.faculty = make_faculty()

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- student ----

    def test_me_as_student_returns_200(self):
        response = self.client.get(self.me_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_as_student_returns_correct_college_id(self):
        response = self.client.get(self.me_url, **auth_header(self.student))
        self.assertEqual(response.data["college_id"], self.student.college_id)

    def test_me_as_student_response_contains_student_profile(self):
        response = self.client.get(self.me_url, **auth_header(self.student))
        self.assertIn("student_profile", response.data)

    def test_me_as_student_response_does_not_contain_faculty_profile(self):
        response = self.client.get(self.me_url, **auth_header(self.student))
        self.assertNotIn("faculty_profile", response.data)

    # ---- faculty ----

    def test_me_as_faculty_returns_200(self):
        response = self.client.get(self.me_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_as_faculty_returns_correct_college_id(self):
        response = self.client.get(self.me_url, **auth_header(self.faculty))
        self.assertEqual(response.data["college_id"], self.faculty.college_id)

    def test_me_as_faculty_response_contains_faculty_profile(self):
        response = self.client.get(self.me_url, **auth_header(self.faculty))
        self.assertIn("faculty_profile", response.data)

    def test_me_as_faculty_response_does_not_contain_student_profile(self):
        response = self.client.get(self.me_url, **auth_header(self.faculty))
        self.assertNotIn("student_profile", response.data)

    # ---- admin ----

    def test_me_as_admin_returns_200(self):
        response = self.client.get(self.me_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_as_admin_returns_correct_college_id(self):
        response = self.client.get(self.me_url, **auth_header(self.admin))
        self.assertEqual(response.data["college_id"], self.admin.college_id)

    # ---- only GET is allowed ----

    def test_me_post_not_allowed_returns_405(self):
        response = self.client.post(
            self.me_url, {}, format="json", **auth_header(self.student)
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_put_not_allowed_returns_405(self):
        response = self.client.put(
            self.me_url, {}, format="json", **auth_header(self.student)
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_delete_not_allowed_returns_405(self):
        response = self.client.delete(self.me_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
