"""
Tests for the attendances app.

Endpoints covered
-----------------
GET   /api/v1/attendance/{course_code}/        – AttendanceListTests
POST  /api/v1/attendance/{course_code}/        – AttendanceSubmitTests
GET   /api/v1/attendance/{course_code}/me/     – AttendanceMeTests
GET   /api/v1/attendance/{course_code}/code/   – AttendanceCodeTests
PATCH /api/v1/attendance/{course_code}/{id}/   – AttendanceManualPatchTests
"""

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# Re-use the auth helpers and user factories from accounts/tests.py
from accounts.tests import (
    auth_header,
    get_list_data,
    make_admin,
    make_department,
    make_faculty,
    make_student,
)
from attendances.models import Attendance
from courses.models import Course, CourseFaculty, Enrollment

CACHE_TTL = 600  # seconds


# ---------------------------------------------------------------------------
# Shared test-data factory helpers
# ---------------------------------------------------------------------------


def make_course(admin, dept, course_code: str = "CS101") -> Course:
    """Create and return a Course."""
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
    """Assign a faculty member to a course with the given role."""
    return CourseFaculty.objects.create(
        course=course,
        faculty=faculty.faculty_profile,
        role=role,
    )


def enroll_student(course: Course, student) -> Enrollment:
    """Enroll a student in a course."""
    return Enrollment.objects.create(
        course=course,
        student=student.student_profile,
    )


def make_attendance(course: Course, student) -> Attendance:
    """Create an Attendance record for today for a student."""
    return Attendance.objects.create(
        course=course,
        student=student.student_profile,
        is_present=True,
    )


# ---------------------------------------------------------------------------
# AttendanceListTests  –  GET /api/v1/attendance/{course_code}/
# ---------------------------------------------------------------------------


class AttendanceListTests(APITestCase):
    """Tests for GET /api/v1/attendance/{course_code}/"""

    def setUp(self):
        cache.clear()
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR010")
        self.assistant = make_faculty("DR011")
        self.student = make_student("202601001")
        self.other_student = make_student("202601002")

        self.course = make_course(self.admin, self.dept, "CS101")
        assign_faculty(self.course, self.faculty, role="lecturer")
        enroll_student(self.course, self.student)

        # Create one attendance record
        self.record = make_attendance(self.course, self.student)

        self.list_url = reverse("v1:attendance-list", kwargs={"course_code": "CS101"})

    # ---- faculty of course → 200, sees all records ----

    def test_list_as_faculty_of_course_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_faculty_of_course_contains_the_record(self):
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        ids = [r["id"] for r in get_list_data(response)]
        self.assertIn(self.record.id, ids)

    # ---- admin → 200 ----

    def test_list_as_admin_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---- student → 403 ----

    def test_list_as_enrolled_student_returns_403(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_list_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# AttendanceSubmitTests  –  POST /api/v1/attendance/{course_code}/
# ---------------------------------------------------------------------------


class AttendanceSubmitTests(APITestCase):
    """Tests for POST /api/v1/attendance/{course_code}/"""

    COURSE_CODE = "CS202"
    CACHE_KEY = f"attendance_{COURSE_CODE}"
    VALID_CODE = "ABC123"

    def setUp(self):
        cache.clear()
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR020")
        self.student = make_student("202601010")
        self.student2 = make_student("202601011")
        self.unenrolled_student = make_student("202601012")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty, role="lecturer")
        enroll_student(self.course, self.student)
        enroll_student(self.course, self.student2)

        self.list_url = reverse(
            "v1:attendance-list", kwargs={"course_code": self.COURSE_CODE}
        )

    # ---- enrolled student, correct code → 201, record created ----

    def test_submit_correct_code_returns_201(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_submit_correct_code_creates_attendance_record(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.student),
        )
        self.assertTrue(
            Attendance.objects.filter(
                course_id=self.COURSE_CODE,
                student=self.student.student_profile,
            ).exists()
        )

    # ---- enrolled student, wrong code → 400 {"detail": "failed"} ----

    def test_submit_wrong_code_returns_400(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        response = self.client.post(
            self.list_url,
            {"code": "WRONG1"},
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("detail"), "failed")

    def test_submit_wrong_code_does_not_create_record(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        self.client.post(
            self.list_url,
            {"code": "WRONG1"},
            format="json",
            **auth_header(self.student),
        )
        self.assertFalse(
            Attendance.objects.filter(
                course_id=self.COURSE_CODE,
                student=self.student.student_profile,
            ).exists()
        )

    # ---- expired code (nothing in cache) → 400 {"detail": "failed"} ----

    def test_submit_expired_code_returns_400(self):
        # cache not set → expired/missing
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("detail"), "failed")

    # ---- student already marked today → 400 {"detail": "already_marked"} ----

    def test_submit_already_marked_returns_400(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        # First submission
        self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.student),
        )
        # Second submission on the same day
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("detail"), "already_marked")

    # ---- not-enrolled student → 403 ----

    def test_submit_unenrolled_student_returns_403(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.unenrolled_student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- faculty submits → 403 ----

    def test_submit_as_faculty_returns_403(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_submit_unauthenticated_returns_401(self):
        cache.set(self.CACHE_KEY, self.VALID_CODE, CACHE_TTL)
        response = self.client.post(
            self.list_url,
            {"code": self.VALID_CODE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# AttendanceMeTests  –  GET /api/v1/attendance/{course_code}/me/
# ---------------------------------------------------------------------------


class AttendanceMeTests(APITestCase):
    """Tests for GET /api/v1/attendance/{course_code}/me/"""

    COURSE_CODE = "CS303"

    def setUp(self):
        cache.clear()
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR030")
        self.student = make_student("202601020")
        self.other_student = make_student("202601021")
        self.unenrolled_student = make_student("202601022")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty, role="lecturer")
        enroll_student(self.course, self.student)
        enroll_student(self.course, self.other_student)

        # Create records for both enrolled students
        self.own_record = make_attendance(self.course, self.student)
        make_attendance(self.course, self.other_student)

        self.me_url = reverse(
            "v1:attendance-me", kwargs={"course_code": self.COURSE_CODE}
        )

    # ---- enrolled student → 200, own records only ----

    def test_me_as_enrolled_student_returns_200(self):
        response = self.client.get(self.me_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_returns_only_own_records(self):
        # me/ endpoint filters by current user — only 1 record was created for this student
        response = self.client.get(self.me_url, **auth_header(self.student))
        records = get_list_data(response)
        self.assertEqual(len(records), 1)

    def test_me_does_not_include_other_students_records(self):
        # other_student also has a record, but me/ must not return it
        response = self.client.get(self.me_url, **auth_header(self.student))
        records = get_list_data(response)
        # Only the current student's single record should be present
        self.assertEqual(len(records), 1)

    # ---- not-enrolled student → 403 ----

    def test_me_unenrolled_student_returns_403(self):
        response = self.client.get(self.me_url, **auth_header(self.unenrolled_student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- faculty → 403 ----

    def test_me_as_faculty_returns_403(self):
        response = self.client.get(self.me_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# AttendanceCodeTests  –  GET /api/v1/attendance/{course_code}/code/
# ---------------------------------------------------------------------------


class AttendanceCodeTests(APITestCase):
    """Tests for GET /api/v1/attendance/{course_code}/code/"""

    COURSE_CODE = "CS404"
    CACHE_KEY = f"attendance_{COURSE_CODE}"

    def setUp(self):
        cache.clear()
        self.dept = make_department()
        self.admin = make_admin()
        self.lecturer = make_faculty("DR040")
        self.assistant = make_faculty("DR041")
        self.student = make_student("202601030")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.lecturer, role="lecturer")
        assign_faculty(self.course, self.assistant, role="assistant")
        enroll_student(self.course, self.student)

        self.code_url = reverse(
            "v1:attendance-code", kwargs={"course_code": self.COURSE_CODE}
        )

    # ---- lecturer, no code in cache → 200, new code generated and cached ----

    def test_code_no_cache_returns_200(self):
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_code_no_cache_response_has_code_and_expires_in(self):
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        self.assertIn("code", response.data)
        self.assertIn("expires_in", response.data)
        self.assertEqual(response.data["expires_in"], CACHE_TTL)

    def test_code_no_cache_saves_code_in_cache(self):
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        cached = cache.get(self.CACHE_KEY)
        self.assertIsNotNone(cached)
        self.assertEqual(cached, response.data["code"])

    def test_code_is_6_characters(self):
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        self.assertEqual(len(response.data["code"]), 6)

    # ---- lecturer, code exists in cache → 200, returns same code, extends TTL ----

    def test_code_existing_cache_returns_same_code(self):
        existing_code = "ZZZ999"
        cache.set(self.CACHE_KEY, existing_code, CACHE_TTL)
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], existing_code)

    def test_code_existing_cache_response_has_expires_in(self):
        cache.set(self.CACHE_KEY, "ZZZ999", CACHE_TTL)
        response = self.client.get(self.code_url, **auth_header(self.lecturer))
        self.assertEqual(response.data["expires_in"], CACHE_TTL)

    # ---- assistant (not lecturer) → 403 ----

    # def test_code_as_assistant_returns_403(self):
    #     response = self.client.get(self.code_url, **auth_header(self.assistant))
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- student → 403 ----

    def test_code_as_student_returns_403(self):
        response = self.client.get(self.code_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_code_unauthenticated_returns_401(self):
        response = self.client.get(self.code_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# AttendanceManualPatchTests  –  PATCH /api/v1/attendance/{course_code}/{id}/
# ---------------------------------------------------------------------------


class AttendanceManualPatchTests(APITestCase):
    """Tests for PATCH /api/v1/attendance/{course_code}/{id}/"""

    COURSE_CODE = "CS505"

    def setUp(self):
        cache.clear()
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR050")
        self.student = make_student("202601040")

        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        assign_faculty(self.course, self.faculty, role="lecturer")
        enroll_student(self.course, self.student)

        self.record = make_attendance(self.course, self.student)
        self.detail_url = reverse(
            "v1:attendance-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": self.record.pk},
        )

    # ---- faculty of course updates is_present → 200 ----

    def test_patch_is_present_as_faculty_returns_200(self):
        response = self.client.patch(
            self.detail_url,
            {"is_present": False},
            format="json",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_is_present_persists_change(self):
        self.client.patch(
            self.detail_url,
            {"is_present": False},
            format="json",
            **auth_header(self.faculty),
        )
        self.record.refresh_from_db()
        self.assertFalse(self.record.is_present)

    def test_patch_can_restore_is_present_to_true(self):
        # First set to False
        self.record.is_present = False
        self.record.save()
        self.client.patch(
            self.detail_url,
            {"is_present": True},
            format="json",
            **auth_header(self.faculty),
        )
        self.record.refresh_from_db()
        self.assertTrue(self.record.is_present)

    # ---- student tries → 403 ----

    def test_patch_as_student_returns_403(self):
        response = self.client.patch(
            self.detail_url,
            {"is_present": False},
            format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_patch_unauthenticated_returns_401(self):
        response = self.client.patch(
            self.detail_url,
            {"is_present": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- nonexistent record → 404 ----

    def test_patch_nonexistent_record_returns_404(self):
        url = reverse(
            "v1:attendance-detail",
            kwargs={"course_code": self.COURSE_CODE, "pk": 99999},
        )
        response = self.client.patch(
            url,
            {"is_present": False},
            format="json",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
