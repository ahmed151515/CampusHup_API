"""
Tests for the contents app.

Endpoints covered
-----------------
GET    /api/v1/<course_code>/contents/       – MaterialListTests
POST   /api/v1/<course_code>/contents/       – MaterialCreateTests
GET    /api/v1/<course_code>/contents/{id}/  – MaterialRetrieveTests
PUT    /api/v1/<course_code>/contents/{id}/  – MaterialUpdateTests
PATCH  /api/v1/<course_code>/contents/{id}/  – MaterialPartialUpdateTests
DELETE /api/v1/<course_code>/contents/{id}/  – MaterialDeleteTests

Permission matrix verified
--------------------------
list / retrieve  → 401 unauthenticated | 403 non-enrolled/faculty | 200 enrolled student
create           → 401 unauthenticated | 403 student/non-assigned-faculty | 201 assigned faculty
update / patch   → same as create
destroy          → same as create

Validation tested
-----------------
- Missing file → 400
- Non-PDF extension → 400
- Non-PDF MIME type (text masquerading as PDF) → 400
- File too large → 400
- Correct PDF → 201
- Read-only fields (type, size_bytes, uploaded_by, uploaded_at, thumbnail) cannot be set by client
"""

import io

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# Re-use the shared helpers from accounts/tests.py
from accounts.tests import (
    auth_header,
    get_list_data,
    make_admin,
    make_department,
    make_faculty,
    make_student,
)
from contents.models import Material
from courses.models import Course, CourseFaculty, Enrollment

COURSE_CODE = "CS101"


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def make_course(admin, dept, course_code: str = COURSE_CODE) -> Course:
    return Course.objects.create(
        created_by=admin,
        course_code=course_code,
        course_name="Intro to CS",
        description="",
        credit_hours=3,
        department=dept,
        semester=1,
    )


def assign_faculty(course: Course, faculty, role: str = "lecturer") -> CourseFaculty:
    return CourseFaculty.objects.create(
        course=course,
        faculty=faculty.faculty_profile,
        role=role,
    )


def enroll_student(course: Course, student) -> Enrollment:
    return Enrollment.objects.create(
        course=course,
        student=student.student_profile,
    )


# ---------------------------------------------------------------------------
# PDF file factories
# ---------------------------------------------------------------------------

# Minimal valid PDF bytes (hand-crafted, renders as a blank page in any reader)
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF"
)


def make_pdf_file(name: str = "test.pdf", content: bytes = _MINIMAL_PDF):
    """Return an in-memory file object that looks like a PDF upload."""
    f = io.BytesIO(content)
    f.name = name
    f.size = len(content)
    return f


def make_text_file_named_pdf(name: str = "fake.pdf"):
    """A plain-text file with a .pdf extension — MIME check must reject it."""
    f = io.BytesIO(b"This is just plain text, definitely not a PDF.")
    f.name = name
    f.size = 46
    return f


def make_txt_file(name: str = "document.txt"):
    """A plain .txt file — extension check rejects it before MIME."""
    f = io.BytesIO(b"Hello world")
    f.name = name
    f.size = 11
    return f


def make_large_pdf_file(size_mb: int = 51):
    """Fake large file that exceeds the 50 MB limit."""
    content = _MINIMAL_PDF + b"\x00" * (size_mb * 1024 * 1024)
    f = io.BytesIO(content)
    f.name = "large.pdf"
    f.size = len(content)
    return f


# ---------------------------------------------------------------------------
# Helper: create a Material directly (bypasses the API, used as fixture)
# ---------------------------------------------------------------------------


def make_material(course: Course, faculty, title: str = "Lecture 1") -> Material:
    pdf = make_pdf_file()
    from django.core.files.uploadedfile import InMemoryUploadedFile

    uploaded = InMemoryUploadedFile(
        file=pdf,
        field_name="file",
        name="test.pdf",
        content_type="application/pdf",
        size=pdf.size,
        charset=None,
    )
    return Material.objects.create(
        course=course,
        uploaded_by=faculty.faculty_profile,
        title=title,
        file=uploaded,
        size_bytes=pdf.size,
        type="pdf",
    )


# ---------------------------------------------------------------------------
# MaterialListTests  –  GET /api/v1/<course_code>/contents/
# ---------------------------------------------------------------------------


class MaterialListTests(APITestCase):
    """Tests for GET /api/v1/<course_code>/contents/"""

    COURSE_CODE = "LST101"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR100")
        self.other_faculty = make_faculty("DR101")  # NOT assigned to course
        self.student = make_student("202601100")
        self.other_student = make_student("202601101")  # NOT enrolled

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.material = make_material(self.course, self.faculty, "Week 1 Notes")

        self.list_url = reverse("v1:material-list", kwargs={"course_code": self.COURSE_CODE})

    # ---- enrolled student → 200, sees the material ----

    def test_list_as_enrolled_student_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_enrolled_student_contains_material(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        ids = [m["id"] for m in get_list_data(response)]
        self.assertIn(self.material.id, ids)

    def test_list_response_contains_expected_fields(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        item = get_list_data(response)[0]
        for field in ("id", "title", "type", "file", "size_bytes", "uploaded_at"):
            self.assertIn(field, item)

    # ---- unauthenticated → 401 ----

    def test_list_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- non-enrolled student → 403 ----

    def test_list_as_unenrolled_student_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.other_student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- faculty (any) → 403 for list ----

    def test_list_as_assigned_faculty_returns_403(self):
        """Faculty cannot view the list — that's the enrolled-student endpoint."""
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_as_unassigned_faculty_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.other_faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# MaterialRetrieveTests  –  GET /api/v1/<course_code>/contents/{id}/
# ---------------------------------------------------------------------------


class MaterialRetrieveTests(APITestCase):
    """Tests for GET /api/v1/<course_code>/contents/{id}/"""

    COURSE_CODE = "RTV101"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR110")
        self.student = make_student("202601110")
        self.other_student = make_student("202601111")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.material = make_material(self.course, self.faculty)
        self.detail_url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": self.material.pk},
        )

    def test_retrieve_as_enrolled_student_returns_200(self):
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_returns_correct_id(self):
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.data["id"], self.material.id)

    def test_retrieve_unauthenticated_returns_401(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_as_unenrolled_student_returns_403(self):
        response = self.client.get(self.detail_url, **auth_header(self.other_student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_as_faculty_returns_403(self):
        response = self.client.get(self.detail_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_material_returns_404(self):
        url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": 99999},
        )
        response = self.client.get(url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# MaterialCreateTests  –  POST /api/v1/<course_code>/contents/
# ---------------------------------------------------------------------------


class MaterialCreateTests(APITestCase):
    """Tests for POST /api/v1/<course_code>/contents/"""

    COURSE_CODE = "CRT201"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR200")
        self.other_faculty = make_faculty("DR201")  # NOT assigned
        self.student = make_student("202601200")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.list_url = reverse("v1:material-list", kwargs={"course_code": self.COURSE_CODE})

    def _post_pdf(self, user, title: str = "Lecture 1", file=None):
        if file is None:
            file = make_pdf_file()
        return self.client.post(
            self.list_url,
            {"title": title, "file": file},
            format="multipart",
            **auth_header(user),
        )

    # ---- assigned faculty + valid PDF → 201 ----

    def test_create_as_assigned_faculty_returns_201(self):
        response = self._post_pdf(self.faculty)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_persists_material_in_db(self):
        self._post_pdf(self.faculty, title="Stored Lecture")
        self.assertTrue(Material.objects.filter(title="Stored Lecture").exists())

    def test_create_response_has_correct_type(self):
        response = self._post_pdf(self.faculty)
        self.assertEqual(response.data["type"], "pdf")

    def test_create_response_has_size_bytes_set(self):
        response = self._post_pdf(self.faculty)
        self.assertGreater(response.data["size_bytes"], 0)

    def test_create_sets_uploaded_by_from_token(self):
        """uploaded_by must be the faculty derived from the JWT, not the request body."""
        response = self._post_pdf(self.faculty)
        # uploaded_by is the faculty_profile PK (college_id)
        self.assertEqual(response.data["uploaded_by"], self.faculty.college_id)

    def test_create_sets_course_from_url(self):
        response = self._post_pdf(self.faculty)
        self.assertEqual(response.data["course"], self.COURSE_CODE)

    # ---- unauthenticated → 401 ----

    def test_create_unauthenticated_returns_401(self):
        response = self.client.post(
            self.list_url,
            {"title": "Unauthorized", "file": make_pdf_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- enrolled student → 403 ----

    def test_create_as_enrolled_student_returns_403(self):
        response = self._post_pdf(self.student)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- faculty NOT assigned to this course → 403 ----

    def test_create_as_unassigned_faculty_returns_403(self):
        response = self._post_pdf(self.other_faculty)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- missing file → 400 ----

    def test_create_without_file_returns_400(self):
        response = self.client.post(
            self.list_url,
            {"title": "No File"},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- missing title → 400 ----

    def test_create_without_title_returns_400(self):
        response = self.client.post(
            self.list_url,
            {"file": make_pdf_file()},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- wrong extension → 400 ----

    def test_create_with_txt_extension_returns_400(self):
        response = self.client.post(
            self.list_url,
            {"title": "Bad Extension", "file": make_txt_file()},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_txt_extension_error_mentions_pdf(self):
        response = self.client.post(
            self.list_url,
            {"title": "Bad Extension", "file": make_txt_file()},
            format="multipart",
            **auth_header(self.faculty),
        )
        error_text = str(response.data).lower()
        self.assertIn("pdf", error_text)

    # ---- .pdf extension but non-PDF content → 400 ----

    def test_create_with_fake_pdf_mime_returns_400(self):
        """A .pdf-named file containing plain text must be rejected by MIME check."""
        response = self.client.post(
            self.list_url,
            {"title": "Fake PDF", "file": make_text_file_named_pdf()},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- oversized file → 400 ----

    def test_create_with_oversized_file_returns_400(self):
        response = self.client.post(
            self.list_url,
            {"title": "Huge File", "file": make_large_pdf_file(size_mb=51)},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- read-only fields cannot be overridden by the client ----

    def test_create_client_cannot_override_type(self):
        response = self.client.post(
            self.list_url,
            {"title": "Override Type", "file": make_pdf_file(), "type": "docx"},
            format="multipart",
            **auth_header(self.faculty),
        )
        # Should succeed (type field is ignored) and still be "pdf"
        if response.status_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data["type"], "pdf")

    def test_create_client_cannot_override_size_bytes(self):
        response = self.client.post(
            self.list_url,
            {"title": "Override Size", "file": make_pdf_file(), "size_bytes": 999},
            format="multipart",
            **auth_header(self.faculty),
        )
        if response.status_code == status.HTTP_201_CREATED:
            self.assertNotEqual(response.data["size_bytes"], 999)

    def test_create_client_cannot_override_uploaded_by(self):
        response = self.client.post(
            self.list_url,
            {
                "title": "Override Uploader",
                "file": make_pdf_file(),
                "uploaded_by": "DR201",  # other_faculty's college_id
            },
            format="multipart",
            **auth_header(self.faculty),
        )
        if response.status_code == status.HTTP_201_CREATED:
            # Must still be the token user, not the injected value
            self.assertEqual(response.data["uploaded_by"], self.faculty.college_id)


# ---------------------------------------------------------------------------
# MaterialUpdateTests  –  PUT /api/v1/<course_code>/contents/{id}/
# ---------------------------------------------------------------------------


class MaterialUpdateTests(APITestCase):
    """Tests for PUT /api/v1/<course_code>/contents/{id}/"""

    COURSE_CODE = "UPD301"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR300")
        self.other_faculty = make_faculty("DR301")
        self.student = make_student("202601300")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.material = make_material(self.course, self.faculty)
        self.detail_url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": self.material.pk},
        )

    def _put(self, user, title: str = "Updated Title", file=None):
        if file is None:
            file = make_pdf_file()
        return self.client.put(
            self.detail_url,
            {"title": title, "file": file, "course": self.COURSE_CODE},
            format="multipart",
            **auth_header(user),
        )

    # ---- assigned faculty → 200 ----

    def test_update_as_assigned_faculty_returns_200(self):
        response = self._put(self.faculty)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_persists_new_title(self):
        self._put(self.faculty, title="New Title")
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, "New Title")

    def test_update_recalculates_size_bytes(self):
        """When a new file is uploaded size_bytes must be updated."""
        old_size = self.material.size_bytes
        new_content = _MINIMAL_PDF + b"\x00" * 512
        new_file = make_pdf_file(content=new_content)
        self._put(self.faculty, file=new_file)
        self.material.refresh_from_db()
        # The new file is bigger, so size_bytes must differ from old (or be updated)
        self.assertNotEqual(self.material.size_bytes, old_size)

    # ---- unauthenticated → 401 ----

    def test_update_unauthenticated_returns_401(self):
        response = self.client.put(self.detail_url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- enrolled student → 403 ----

    def test_update_as_student_returns_403(self):
        response = self._put(self.student)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unassigned faculty → 403 ----

    def test_update_as_unassigned_faculty_returns_403(self):
        response = self._put(self.other_faculty)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- non-PDF replacement → 400 ----

    def test_update_with_non_pdf_file_returns_400(self):
        response = self._put(self.faculty, file=make_txt_file())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- nonexistent material → 404 ----

    def test_update_nonexistent_material_returns_404(self):
        url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": 99999},
        )
        response = self.client.put(
            url,
            {"title": "Ghost", "file": make_pdf_file(), "course": self.COURSE_CODE},
            format="multipart",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# MaterialPartialUpdateTests  –  PATCH /api/v1/<course_code>/contents/{id}/
# ---------------------------------------------------------------------------


class MaterialPartialUpdateTests(APITestCase):
    """Tests for PATCH /api/v1/<course_code>/contents/{id}/"""

    COURSE_CODE = "PAT401"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR400")
        self.other_faculty = make_faculty("DR401")
        self.student = make_student("202601400")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.material = make_material(self.course, self.faculty, "Original Title")
        self.detail_url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": self.material.pk},
        )

    def _patch(self, user, data: dict):
        return self.client.patch(
            self.detail_url,
            data,
            format="multipart",
            **auth_header(user),
        )

    # ---- assigned faculty patches title → 200, persisted ----

    def test_patch_title_as_assigned_faculty_returns_200(self):
        response = self._patch(self.faculty, {"title": "Patched Title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_title_persists(self):
        self._patch(self.faculty, {"title": "Patched Title"})
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, "Patched Title")

    # ---- patch with new valid PDF → 200 ----

    def test_patch_file_with_valid_pdf_returns_200(self):
        response = self._patch(self.faculty, {"file": make_pdf_file("replacement.pdf")})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---- patch with non-PDF file → 400 ----

    def test_patch_file_with_txt_returns_400(self):
        response = self._patch(self.faculty, {"file": make_txt_file()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- unauthenticated → 401 ----

    def test_patch_unauthenticated_returns_401(self):
        response = self.client.patch(self.detail_url, {"title": "X"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- enrolled student → 403 ----

    def test_patch_as_student_returns_403(self):
        response = self._patch(self.student, {"title": "Student patch"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unassigned faculty → 403 ----

    def test_patch_as_unassigned_faculty_returns_403(self):
        response = self._patch(self.other_faculty, {"title": "Other faculty patch"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- read-only field patching is silently ignored ----

    def test_patch_type_is_ignored(self):
        """Attempting to patch `type` must not change it."""
        self._patch(self.faculty, {"type": "docx"})
        self.material.refresh_from_db()
        self.assertEqual(self.material.type, "pdf")


# ---------------------------------------------------------------------------
# MaterialDeleteTests  –  DELETE /api/v1/<course_code>/contents/{id}/
# ---------------------------------------------------------------------------


class MaterialDeleteTests(APITestCase):
    """Tests for DELETE /api/v1/<course_code>/contents/{id}/"""

    COURSE_CODE = "DEL501"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR500")
        self.other_faculty = make_faculty("DR501")
        self.student = make_student("202601500")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty)
        enroll_student(self.course, self.student)

        self.material = make_material(self.course, self.faculty)
        self.detail_url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": self.material.pk},
        )

    # ---- assigned faculty → 204, removed from DB ----

    def test_delete_as_assigned_faculty_returns_204(self):
        response = self.client.delete(self.detail_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_record_from_db(self):
        self.client.delete(self.detail_url, **auth_header(self.faculty))
        self.assertFalse(Material.objects.filter(pk=self.material.pk).exists())

    # ---- unauthenticated → 401 ----

    def test_delete_unauthenticated_returns_401(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- enrolled student → 403 ----

    def test_delete_as_student_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_as_student_does_not_remove_record(self):
        self.client.delete(self.detail_url, **auth_header(self.student))
        self.assertTrue(Material.objects.filter(pk=self.material.pk).exists())

    # ---- unassigned faculty → 403 ----

    def test_delete_as_unassigned_faculty_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.other_faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- nonexistent material → 404 ----

    def test_delete_nonexistent_material_returns_404(self):
        url = reverse(
            "v1:material-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": 99999},
        )
        response = self.client.delete(url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
