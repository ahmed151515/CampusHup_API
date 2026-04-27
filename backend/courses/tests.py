"""
Tests for the courses app.

Endpoints covered
-----------------
GET    /api/v1/courses/               – CourseListTests
POST   /api/v1/courses/               – CourseCreateTests
GET    /api/v1/courses/{course_code}/ – CourseRetrieveTests
PUT    /api/v1/courses/{course_code}/ – CourseUpdateTests
PATCH  /api/v1/courses/{course_code}/ – CourseUpdateTests
DELETE /api/v1/courses/{course_code}/ – CourseDeleteTests

Model tests
-----------
CourseModelTests
CourseFacultyModelTests
EnrollmentModelTests
TimetableModelTests
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests import (
    auth_header,
    get_list_data,
    make_admin,
    make_department,
    make_faculty,
    make_student,
)
from courses.models import Course, CourseFaculty, Enrollment, Timetable


# ---------------------------------------------------------------------------
# Shared test-data factory helpers
# ---------------------------------------------------------------------------


def make_course(admin, dept, course_code: str = "CS101") -> Course:
    """Create and return a Course."""
    return Course.objects.create(
        created_by=admin,
        course_code=course_code,
        course_name="Intro to CS",
        description="A basic intro course.",
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


# ---------------------------------------------------------------------------
# CourseListTests  –  GET /api/v1/courses/
# ---------------------------------------------------------------------------


class CourseListTests(APITestCase):
    """Tests for GET /api/v1/courses/"""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR001")
        self.student = make_student("202601001")
        self.course = make_course(self.admin, self.dept, "CS101")
        self.course2 = make_course(self.admin, self.dept, "CS201")
        self.list_url = reverse("v1:course-list")

    # ---- authenticated users → 200 ----

    def test_list_as_admin_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_faculty_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_student_returns_200(self):
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_student_only_returns_enrolled_courses(self):
        # Student is not enrolled initially
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(len(response.data), 0)

        # Enroll student
        enroll_student(self.course, self.student)
        response = self.client.get(self.list_url, **auth_header(self.student))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["course_code"], self.course.course_code)

    def test_list_contains_created_course(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        codes = [c["course_code"] for c in get_list_data(response)]
        self.assertIn(self.course.course_code, codes)

    def test_list_is_ordered_by_course_code(self):
        response = self.client.get(self.list_url, **auth_header(self.admin))
        codes = [c["course_code"] for c in get_list_data(response)]
        self.assertEqual(codes, sorted(codes))

    # ---- unauthenticated → 401 ----

    def test_list_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# CourseCreateTests  –  POST /api/v1/courses/
# ---------------------------------------------------------------------------


class CourseCreateTests(APITestCase):
    """Tests for POST /api/v1/courses/"""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR002")
        self.student = make_student("202601002")
        self.list_url = reverse("v1:course-list")
        self.valid_payload = {
            "course_code": "CS999",
            "course_name": "Test Course",
            "description": "A test course.",
            "credit_hours": 3,
            "department": self.dept.code,
            "semester": 2,
        }

    # ---- admin → 201 ----

    def test_create_as_admin_returns_201(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_persists_in_db(self):
        self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.admin),
        )
        self.assertTrue(
            Course.objects.filter(course_code=self.valid_payload["course_code"]).exists()
        )

    def test_create_sets_created_by_to_request_user(self):
        self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.admin),
        )
        course = Course.objects.get(course_code=self.valid_payload["course_code"])
        self.assertEqual(course.created_by, self.admin)

    # ---- validation errors → 400 ----

    def test_create_missing_required_field_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "course_name"}
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_course_code_returns_400(self):
        make_course(self.admin, self.dept, self.valid_payload["course_code"])
        response = self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_semester_above_14_returns_400(self):
        payload = {**self.valid_payload, "semester": 15}
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_semester_below_1_returns_400(self):
        payload = {**self.valid_payload, "semester": 0}
        response = self.client.post(
            self.list_url, payload, format="json", **auth_header(self.admin)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- non-admin → 403 ----

    def test_create_as_faculty_returns_403(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_as_student_returns_403(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_create_unauthenticated_returns_401(self):
        response = self.client.post(self.list_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# CourseRetrieveTests  –  GET /api/v1/courses/{course_code}/
# ---------------------------------------------------------------------------


class CourseRetrieveTests(APITestCase):
    """Tests for GET /api/v1/courses/{course_code}/"""

    COURSE_CODE = "CS110"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR003")
        self.student = make_student("202601003")
        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        self.detail_url = reverse("v1:course-detail", kwargs={"course_code": self.COURSE_CODE})

    # ---- authenticated reads → 200 ----

    def test_retrieve_as_admin_returns_200(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_enrolled_student_returns_200(self):
        enroll_student(self.course, self.student)
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_unenrolled_student_returns_404(self):
        response = self.client.get(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_response_contains_expected_fields(self):
        response = self.client.get(self.detail_url, **auth_header(self.admin))
        for field in (
            "course_code",
            "course_name",
            "description",
            "credit_hours",
            "department",
            "semester",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
        ):
            self.assertIn(field, response.data)

    # ---- 404 ----

    def test_retrieve_nonexistent_course_returns_404(self):
        url = reverse("v1:course-detail", kwargs={"course_code": "NOTEXIST"})
        response = self.client.get(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- unauthenticated → 401 ----

    def test_retrieve_unauthenticated_returns_401(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# CourseUpdateTests  –  PUT/PATCH /api/v1/courses/{course_code}/
# ---------------------------------------------------------------------------


class CourseUpdateTests(APITestCase):
    """Tests for PUT/PATCH /api/v1/courses/{course_code}/"""

    COURSE_CODE = "CS120"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR004")
        self.student = make_student("202601004")
        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        self.detail_url = reverse("v1:course-detail", kwargs={"course_code": self.COURSE_CODE})
        self.full_payload = {
            "course_code": self.COURSE_CODE,
            "course_name": "Updated Course Name",
            "description": "Updated description.",
            "credit_hours": 4,
            "department": self.dept.code,
            "semester": 3,
        }

    # ---- admin full update (PUT) → 200 ----

    def test_full_update_as_admin_returns_200(self):
        response = self.client.put(
            self.detail_url, self.full_payload, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_full_update_persists_changes(self):
        self.client.put(
            self.detail_url, self.full_payload, format="json",
            **auth_header(self.admin),
        )
        self.course.refresh_from_db()
        self.assertEqual(self.course.course_name, "Updated Course Name")

    # ---- admin partial update (PATCH) → 200 ----

    def test_partial_update_course_name_as_admin(self):
        response = self.client.patch(
            self.detail_url, {"course_name": "Patched Name"}, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.course_name, "Patched Name")

    def test_partial_update_semester_as_admin(self):
        response = self.client.patch(
            self.detail_url, {"semester": 5}, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.semester, 5)

    # ---- non-admin → 403 ----

    def test_update_as_faculty_returns_403(self):
        response = self.client.patch(
            self.detail_url, {"course_name": "Hacked"}, format="json",
            **auth_header(self.faculty),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_as_student_returns_403(self):
        response = self.client.patch(
            self.detail_url, {"course_name": "Hacked"}, format="json",
            **auth_header(self.student),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_update_unauthenticated_returns_401(self):
        response = self.client.patch(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- 404 ----

    def test_update_nonexistent_course_returns_404(self):
        url = reverse("v1:course-detail", kwargs={"course_code": "NOTEXIST"})
        response = self.client.patch(
            url, {"course_name": "Ghost"}, format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# CourseDeleteTests  –  DELETE /api/v1/courses/{course_code}/
# ---------------------------------------------------------------------------


class CourseDeleteTests(APITestCase):
    """Tests for DELETE /api/v1/courses/{course_code}/"""

    COURSE_CODE = "CS130"

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR005")
        self.student = make_student("202601005")
        self.course = make_course(self.admin, self.dept, self.COURSE_CODE)
        self.detail_url = reverse("v1:course-detail", kwargs={"course_code": self.COURSE_CODE})

    # ---- admin → 204 ----

    def test_delete_as_admin_returns_204(self):
        response = self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_course_from_db(self):
        self.client.delete(self.detail_url, **auth_header(self.admin))
        self.assertFalse(Course.objects.filter(course_code=self.COURSE_CODE).exists())

    # ---- non-admin → 403 ----

    def test_delete_as_faculty_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.faculty))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_as_student_returns_403(self):
        response = self.client.delete(self.detail_url, **auth_header(self.student))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- unauthenticated → 401 ----

    def test_delete_unauthenticated_returns_401(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- 404 ----

    def test_delete_nonexistent_course_returns_404(self):
        url = reverse("v1:course-detail", kwargs={"course_code": "NOTEXIST"})
        response = self.client.delete(url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# CourseModelTests  –  model-layer unit tests
# ---------------------------------------------------------------------------


class CourseModelTests(APITestCase):
    """Unit tests for the Course model."""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.course = make_course(self.admin, self.dept, "CS140")

    def test_str_representation(self):
        self.assertEqual(str(self.course), "CS140 - Intro to CS")

    def test_course_code_is_primary_key(self):
        self.assertEqual(self.course._meta.pk.name, "course_code")

    def test_default_is_active_true(self):
        self.assertTrue(self.course.is_active)

    def test_semester_min_validator(self):
        course = Course(
            created_by=self.admin,
            course_code="CS_BAD1",
            course_name="Bad Semester",
            credit_hours=3,
            department=self.dept,
            semester=0,
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_semester_max_validator(self):
        course = Course(
            created_by=self.admin,
            course_code="CS_BAD2",
            course_name="Bad Semester",
            credit_hours=3,
            department=self.dept,
            semester=15,
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_created_by_set_null_on_user_delete(self):
        self.admin.delete()
        self.course.refresh_from_db()
        self.assertIsNone(self.course.created_by)


# ---------------------------------------------------------------------------
# CourseFacultyModelTests  –  model-layer unit tests
# ---------------------------------------------------------------------------


class CourseFacultyModelTests(APITestCase):
    """Unit tests for the CourseFaculty model."""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR006")
        self.course = make_course(self.admin, self.dept, "CS150")

    def test_str_representation(self):
        cf = assign_faculty(self.course, self.faculty, role="lecturer")
        expected = f"{self.faculty.faculty_profile} - {self.course} (lecturer)"
        self.assertEqual(str(cf), expected)

    def test_unique_together_course_faculty(self):
        assign_faculty(self.course, self.faculty, role="lecturer")
        with self.assertRaises(IntegrityError):
            CourseFaculty.objects.create(
                course=self.course,
                faculty=self.faculty.faculty_profile,
                role="assistant",
            )

    def test_role_choices_lecturer(self):
        cf = assign_faculty(self.course, self.faculty, role="lecturer")
        self.assertEqual(cf.role, "lecturer")

    def test_role_choices_assistant(self):
        faculty2 = make_faculty("DR007")
        cf = assign_faculty(self.course, faculty2, role="assistant")
        self.assertEqual(cf.role, "assistant")


# ---------------------------------------------------------------------------
# EnrollmentModelTests  –  model-layer unit tests
# ---------------------------------------------------------------------------


class EnrollmentModelTests(APITestCase):
    """Unit tests for the Enrollment model."""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.student = make_student("202601006")
        self.course = make_course(self.admin, self.dept, "CS160")

    def test_str_representation(self):
        enrollment = enroll_student(self.course, self.student)
        expected = f"{self.student.student_profile} enrolled in {self.course}"
        self.assertEqual(str(enrollment), expected)

    def test_unique_together_student_course(self):
        enroll_student(self.course, self.student)
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(
                course=self.course,
                student=self.student.student_profile,
            )

    def test_default_status_active(self):
        enrollment = enroll_student(self.course, self.student)
        self.assertEqual(enrollment.status, "active")

    def test_grade_nullable(self):
        enrollment = enroll_student(self.course, self.student)
        self.assertIsNone(enrollment.grade)


# ---------------------------------------------------------------------------
# TimetableModelTests  –  model-layer unit tests
# ---------------------------------------------------------------------------


class TimetableModelTests(APITestCase):
    """Unit tests for the Timetable model."""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty = make_faculty("DR008")
        self.course = make_course(self.admin, self.dept, "CS170")

    def _make_timetable(self, day: str = "Mon") -> Timetable:
        return Timetable.objects.create(
            course=self.course,
            faculty=self.faculty.faculty_profile,
            day_of_week=day,
            start_time="09:00:00",
            end_time="10:30:00",
            room="B101",
            semester="Spring 2025",
        )

    def test_str_representation(self):
        tt = self._make_timetable("Mon")
        self.assertEqual(str(tt), f"{self.course} schedule on Mon")

    def test_day_of_week_choices(self):
        for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat"):
            tt = self._make_timetable(day)
            self.assertEqual(tt.day_of_week, day)
            tt.delete()


# ---------------------------------------------------------------------------
# CourseActionTests  –  Custom actions for enrollment and faculty
# ---------------------------------------------------------------------------


class CourseActionTests(APITestCase):
    """Tests for custom actions in CourseViewSet."""

    def setUp(self):
        self.dept = make_department()
        self.admin = make_admin()
        self.faculty_user = make_faculty("DR_TEST_01")
        self.student_user = make_student("ST_TEST_01")
        self.course = make_course(self.admin, self.dept, "CS301")
        
        self.enroll_url = reverse("v1:course-enroll-student", kwargs={"course_code": "CS301"})
        self.list_enrollments_url = reverse("v1:course-list-enrollments", kwargs={"course_code": "CS301"})
        self.assign_faculty_url = reverse("v1:course-assign-faculty", kwargs={"course_code": "CS301"})
        self.list_faculty_url = reverse("v1:course-list-faculty", kwargs={"course_code": "CS301"})

    # ---- Enrollment Tests ----

    def test_enroll_student_as_admin_returns_201(self):
        payload = {"student": self.student_user.college_id}
        response = self.client.post(self.enroll_url, payload, format="json", **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Enrollment.objects.filter(course=self.course, student=self.student_user.student_profile).exists())

    def test_enroll_student_as_student_returns_403(self):
        payload = {"student": self.student_user.college_id}
        response = self.client.post(self.enroll_url, payload, format="json", **auth_header(self.student_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_enrollments_as_admin_returns_200(self):
        enroll_student(self.course, self.student_user)
        response = self.client.get(self.list_enrollments_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student"], self.student_user.college_id)

    def test_list_enrollments_as_student_returns_403(self):
        enroll_student(self.course, self.student_user)
        response = self.client.get(self.list_enrollments_url, **auth_header(self.student_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enroll_student_duplicate_returns_400(self):
        # Enroll once
        enroll_student(self.course, self.student_user)
        
        # Try to enroll again
        payload = {"student": self.student_user.college_id}
        response = self.client.post(self.enroll_url, payload, format="json", **auth_header(self.admin))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already enrolled", response.data["detail"])

    # ---- Faculty Assignment Tests ----

    def test_assign_faculty_as_admin_returns_201(self):
        payload = {"faculty": self.faculty_user.college_id, "role": "lecturer"}
        response = self.client.post(self.assign_faculty_url, payload, format="json", **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CourseFaculty.objects.filter(course=self.course, faculty=self.faculty_user.faculty_profile).exists())

    def test_assign_faculty_as_faculty_returns_403(self):
        payload = {"faculty": self.faculty_user.college_id, "role": "lecturer"}
        response = self.client.post(self.assign_faculty_url, payload, format="json", **auth_header(self.faculty_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_faculty_as_admin_returns_200(self):
        assign_faculty(self.course, self.faculty_user)
        response = self.client.get(self.list_faculty_url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["faculty"], self.faculty_user.college_id)

    def test_list_faculty_as_student_returns_403(self):
        assign_faculty(self.course, self.faculty_user)
        response = self.client.get(self.list_faculty_url, **auth_header(self.student_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_faculty_duplicate_role_returns_400(self):
        # Assign first lecturer
        assign_faculty(self.course, self.faculty_user, role="lecturer")
        
        # Try to assign second lecturer
        faculty2 = make_faculty("DR_TEST_02")
        payload = {"faculty": faculty2.college_id, "role": "lecturer"}
        response = self.client.post(self.assign_faculty_url, payload, format="json", **auth_header(self.admin))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", response.data["detail"])
