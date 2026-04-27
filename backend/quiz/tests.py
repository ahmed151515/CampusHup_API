"""
Tests for the quiz app.

Endpoints covered
-----------------
GET    /api/v1/<course_code>/quiz/                        – list quizzes
POST   /api/v1/<course_code>/quiz/                        – create quiz
GET    /api/v1/<course_code>/quiz/{id}/                   – retrieve quiz
PUT    /api/v1/<course_code>/quiz/{id}/                   – full update
PATCH  /api/v1/<course_code>/quiz/{id}/                   – partial update
DELETE /api/v1/<course_code>/quiz/{id}/                   – delete
POST   /api/v1/<course_code>/quiz/{id}/start/             – start quiz
POST   /api/v1/<course_code>/quiz/{id}/submit/            – submit answers
GET    /api/v1/<course_code>/quiz/{id}/submissions/       – faculty view all
GET    /api/v1/<course_code>/quiz/{id}/my-grade/          – student own grade
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests import (
    auth_header,
    make_admin,
    make_department,
    make_faculty,
    make_student,
)
from courses.models import CourseFaculty, Enrollment, Course
from quiz.models import Quiz, Question, QuizSubmission, SubmissionAnswer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_course(dept, code="CS101"):
    return Course.objects.get_or_create(
        course_code=code,
        defaults={
            "course_name": "Test Course",
            "credit_hours": 3,
            "department": dept,
            "semester": 1,
        },
    )[0]


def make_quiz(course, faculty_user, title="Test Quiz", duration=60):
    return Quiz.objects.create(
        course=course,
        title=title,
        description="A test quiz",
        duration_minutes=duration,
        created_by=faculty_user.faculty_profile,
    )


def make_question(quiz, order=1, correct=1, marks=2):
    return Question.objects.create(
        quiz=quiz,
        text=f"Question {order}",
        order=order,
        marks=marks,
        choice_1="A",
        choice_2="B",
        choice_3="C",
        choice_4="D",
        correct_choice=correct,
    )


def quiz_list_url(course_code):
    return f"/api/v1/{course_code}/quiz/"


def quiz_detail_url(course_code, quiz_id):
    return f"/api/v1/{course_code}/quiz/{quiz_id}/"


def quiz_action_url(course_code, quiz_id, action):
    return f"/api/v1/{course_code}/quiz/{quiz_id}/{action}/"


VALID_QUIZ_PAYLOAD = {
    "title": "New Quiz",
    "description": "desc",
    "duration_minutes": 30,
    "questions": [
        {
            "text": "Q1",
            "order": 1,
            "marks": 1,
            "choice_1": "A",
            "choice_2": "B",
            "choice_3": "C",
            "choice_4": "D",
            "correct_choice": 1,
        }
    ],
}


# ---------------------------------------------------------------------------
# Shared setUp mixin
# ---------------------------------------------------------------------------

class QuizTestBase(APITestCase):
    """
    Creates:
      - dept, course
      - faculty assigned to course (CourseFaculty)
      - student enrolled in course (Enrollment)
      - another faculty NOT assigned to this course
      - quiz with 2 questions (marks=2 each, correct=1)
    """

    def setUp(self):
        self.dept = make_department()
        self.course = make_course(self.dept)

        self.faculty_user = make_faculty("DR001")
        CourseFaculty.objects.get_or_create(
            course=self.course,
            faculty=self.faculty_user.faculty_profile,
            defaults={"role": "lecturer"},
        )

        self.student_user = make_student("202601001")
        Enrollment.objects.get_or_create(
            course=self.course,
            student=self.student_user.student_profile,
        )

        self.other_faculty = make_faculty("DR002")  # not assigned to course
        self.admin_user = make_admin()

        self.quiz = make_quiz(self.course, self.faculty_user)
        self.q1 = make_question(self.quiz, order=1, correct=1, marks=2)
        self.q2 = make_question(self.quiz, order=2, correct=2, marks=2)

        self.list_url = quiz_list_url(self.course.course_code)
        self.detail_url = quiz_detail_url(self.course.course_code, self.quiz.pk)


# ---------------------------------------------------------------------------
# QuizListTests
# ---------------------------------------------------------------------------

class QuizListTests(QuizTestBase):
    """GET /api/v1/<course_code>/quiz/"""

    def test_list_as_faculty_returns_200(self):
        r = self.client.get(self.list_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_as_student_returns_200(self):
        r = self.client.get(self.list_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_as_admin_returns_200(self):
        r = self.client.get(self.list_url, **auth_header(self.admin_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_unauthenticated_returns_401(self):
        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_contains_quiz(self):
        r = self.client.get(self.list_url, **auth_header(self.faculty_user))
        ids = [q["id"] for q in r.data]
        self.assertIn(self.quiz.pk, ids)

    def test_list_includes_question_count(self):
        r = self.client.get(self.list_url, **auth_header(self.faculty_user))
        item = next(q for q in r.data if q["id"] == self.quiz.pk)
        self.assertEqual(item["question_count"], 2)


# ---------------------------------------------------------------------------
# QuizCreateTests
# ---------------------------------------------------------------------------

class QuizCreateTests(QuizTestBase):
    """POST /api/v1/<course_code>/quiz/"""

    def test_create_as_faculty_returns_201(self):
        r = self.client.post(
            self.list_url, VALID_QUIZ_PAYLOAD, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_as_admin_returns_403(self):
        r = self.client.post(
            self.list_url, VALID_QUIZ_PAYLOAD, format="json",
            **auth_header(self.admin_user)
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_as_student_returns_403(self):
        r = self.client.post(
            self.list_url, VALID_QUIZ_PAYLOAD, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_unauthenticated_returns_401(self):
        r = self.client.post(self.list_url, VALID_QUIZ_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_persists_quiz_in_db(self):
        self.client.post(
            self.list_url, VALID_QUIZ_PAYLOAD, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertTrue(Quiz.objects.filter(title="New Quiz").exists())

    def test_create_persists_nested_questions(self):
        self.client.post(
            self.list_url, VALID_QUIZ_PAYLOAD, format="json",
            **auth_header(self.faculty_user)
        )
        quiz = Quiz.objects.get(title="New Quiz")
        self.assertEqual(quiz.questions.count(), 1)

    def test_create_missing_title_returns_400(self):
        payload = {**VALID_QUIZ_PAYLOAD, "title": ""}
        r = self.client.post(
            self.list_url, payload, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_duration_returns_400(self):
        payload = {k: v for k, v in VALID_QUIZ_PAYLOAD.items() if k != "duration_minutes"}
        r = self.client.post(
            self.list_url, payload, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# QuizRetrieveTests
# ---------------------------------------------------------------------------

class QuizRetrieveTests(QuizTestBase):
    """GET /api/v1/<course_code>/quiz/{id}/"""

    def test_retrieve_as_faculty_returns_200(self):
        r = self.client.get(self.detail_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_retrieve_as_student_returns_200(self):
        r = self.client.get(self.detail_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_retrieve_unauthenticated_returns_401(self):
        r = self.client.get(self.detail_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_contains_questions(self):
        r = self.client.get(self.detail_url, **auth_header(self.student_user))
        self.assertIn("questions", r.data)
        self.assertEqual(len(r.data["questions"]), 2)

    def test_retrieve_student_cannot_see_correct_choice(self):
        r = self.client.get(self.detail_url, **auth_header(self.student_user))
        for q in r.data["questions"]:
            self.assertNotIn("correct_choice", q)

    def test_retrieve_faculty_can_see_correct_choice(self):
        r = self.client.get(self.detail_url, **auth_header(self.faculty_user))
        for q in r.data["questions"]:
            self.assertIn("correct_choice", q)

    def test_retrieve_nonexistent_quiz_returns_404(self):
        url = quiz_detail_url(self.course.course_code, 99999)
        r = self.client.get(url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# QuizUpdateTests
# ---------------------------------------------------------------------------

class QuizUpdateTests(QuizTestBase):
    """PUT/PATCH /api/v1/<course_code>/quiz/{id}/"""

    def test_partial_update_as_faculty_returns_200(self):
        r = self.client.patch(
            self.detail_url, {"title": "Updated"}, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_partial_update_persists_title(self):
        self.client.patch(
            self.detail_url, {"title": "Changed"}, format="json",
            **auth_header(self.faculty_user)
        )
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "Changed")

    def test_partial_update_as_student_returns_403(self):
        r = self.client.patch(
            self.detail_url, {"title": "X"}, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_blocked_when_submissions_exist(self):
        QuizSubmission.objects.create(
            quiz=self.quiz,
            student=self.student_user.student_profile,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
            score=2,
        )
        r = self.client.patch(
            self.detail_url, {"title": "X"}, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_unauthenticated_returns_401(self):
        r = self.client.patch(self.detail_url, {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_as_admin_returns_403(self):
        r = self.client.patch(
            self.detail_url, {"title": "X"}, format="json",
            **auth_header(self.admin_user)
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# QuizDeleteTests
# ---------------------------------------------------------------------------

class QuizDeleteTests(QuizTestBase):
    """DELETE /api/v1/<course_code>/quiz/{id}/"""

    def test_delete_as_faculty_returns_204(self):
        r = self.client.delete(self.detail_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_quiz_from_db(self):
        quiz_id = self.quiz.pk
        self.client.delete(self.detail_url, **auth_header(self.faculty_user))
        self.assertFalse(Quiz.objects.filter(pk=quiz_id).exists())

    def test_delete_as_student_returns_403(self):
        r = self.client.delete(self.detail_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_unauthenticated_returns_401(self):
        r = self.client.delete(self.detail_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_blocked_when_submissions_exist(self):
        QuizSubmission.objects.create(
            quiz=self.quiz,
            student=self.student_user.student_profile,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
            score=2,
        )
        r = self.client.delete(self.detail_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_as_admin_returns_403(self):
        r = self.client.delete(self.detail_url, **auth_header(self.admin_user))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# QuizStartTests
# ---------------------------------------------------------------------------

class QuizStartTests(QuizTestBase):
    """POST /api/v1/<course_code>/quiz/{id}/start/"""

    def setUp(self):
        super().setUp()
        self.start_url = quiz_action_url(self.course.course_code, self.quiz.pk, "start")

    def test_start_as_student_returns_200(self):
        r = self.client.post(self.start_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_start_creates_submission(self):
        self.client.post(self.start_url, **auth_header(self.student_user))
        self.assertTrue(
            QuizSubmission.objects.filter(
                quiz=self.quiz, student=self.student_user.student_profile
            ).exists()
        )

    def test_start_sets_started_at(self):
        self.client.post(self.start_url, **auth_header(self.student_user))
        sub = QuizSubmission.objects.get(
            quiz=self.quiz, student=self.student_user.student_profile
        )
        self.assertIsNotNone(sub.started_at)

    def test_start_returns_started_at_in_response(self):
        r = self.client.post(self.start_url, **auth_header(self.student_user))
        self.assertIn("started_at", r.data)

    def test_start_idempotent_second_call_returns_200(self):
        self.client.post(self.start_url, **auth_header(self.student_user))
        r = self.client.post(self.start_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_start_idempotent_no_duplicate_submissions(self):
        self.client.post(self.start_url, **auth_header(self.student_user))
        self.client.post(self.start_url, **auth_header(self.student_user))
        count = QuizSubmission.objects.filter(
            quiz=self.quiz, student=self.student_user.student_profile
        ).count()
        self.assertEqual(count, 1)

    def test_start_empty_quiz_returns_400(self):
        empty_quiz = make_quiz(self.course, self.faculty_user, title="Empty")
        url = quiz_action_url(self.course.course_code, empty_quiz.pk, "start")
        r = self.client.post(url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_as_faculty_returns_403(self):
        r = self.client.post(self.start_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_unauthenticated_returns_401(self):
        r = self.client.post(self.start_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# QuizSubmitTests
# ---------------------------------------------------------------------------

class QuizSubmitTests(QuizTestBase):
    """POST /api/v1/<course_code>/quiz/{id}/submit/"""

    def setUp(self):
        super().setUp()
        self.submit_url = quiz_action_url(self.course.course_code, self.quiz.pk, "submit")
        self.valid_answers = {
            "answers": [
                {"question_id": self.q1.pk, "selected_choice": 1},  # correct
                {"question_id": self.q2.pk, "selected_choice": 2},  # correct
            ]
        }

    def test_submit_as_student_returns_200(self):
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_submit_returns_score(self):
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertIn("score", r.data)

    def test_submit_calculates_score_correctly(self):
        """Both answers correct → score = 2+2 = 4."""
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(float(r.data["score"]), 4.0)

    def test_submit_partial_answers_accepted(self):
        """Answering only one question is allowed."""
        payload = {"answers": [{"question_id": self.q1.pk, "selected_choice": 1}]}
        r = self.client.post(
            self.submit_url, payload, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_submit_partial_score_is_correct(self):
        """One correct answer out of two → score = 2."""
        payload = {"answers": [{"question_id": self.q1.pk, "selected_choice": 1}]}
        r = self.client.post(
            self.submit_url, payload, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(float(r.data["score"]), 2.0)

    def test_submit_wrong_answers_score_zero(self):
        """All wrong answers → score = 0."""
        payload = {
            "answers": [
                {"question_id": self.q1.pk, "selected_choice": 2},  # wrong
                {"question_id": self.q2.pk, "selected_choice": 1},  # wrong
            ]
        }
        r = self.client.post(
            self.submit_url, payload, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(float(r.data["score"]), 0.0)

    def test_submit_sets_submitted_at(self):
        self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        sub = QuizSubmission.objects.get(
            quiz=self.quiz, student=self.student_user.student_profile
        )
        self.assertIsNotNone(sub.submitted_at)

    def test_submit_without_start_auto_starts(self):
        """Submit without calling /start/ first — auto-creates submission."""
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sub = QuizSubmission.objects.get(
            quiz=self.quiz, student=self.student_user.student_profile
        )
        self.assertIsNotNone(sub.started_at)

    def test_double_submit_returns_400(self):
        self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_after_time_expired_returns_400(self):
        """Submission is already started but time has expired."""
        sub = QuizSubmission.objects.create(
            quiz=self.quiz,
            student=self.student_user.student_profile,
            started_at=timezone.now() - timedelta(minutes=self.quiz.duration_minutes + 1),
        )
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_as_faculty_returns_403(self):
        r = self.client.post(
            self.submit_url, self.valid_answers, format="json",
            **auth_header(self.faculty_user)
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_unauthenticated_returns_401(self):
        r = self.client.post(self.submit_url, self.valid_answers, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_foreign_question_rejected(self):
        """Submitting a question ID from another quiz returns 400."""
        other_quiz = make_quiz(self.course, self.faculty_user, title="Other")
        other_q = make_question(other_quiz, order=1)
        payload = {"answers": [{"question_id": other_q.pk, "selected_choice": 1}]}
        r = self.client.post(
            self.submit_url, payload, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_empty_quiz_rejected(self):
        """Submitting an empty quiz directly returns 400."""
        empty_quiz = make_quiz(self.course, self.faculty_user, title="Empty")
        url = quiz_action_url(self.course.course_code, empty_quiz.pk, "submit")
        payload = {"answers": []}
        r = self.client.post(
            url, payload, format="json",
            **auth_header(self.student_user)
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# QuizSubmissionsTests
# ---------------------------------------------------------------------------

class QuizSubmissionsTests(QuizTestBase):
    """GET /api/v1/<course_code>/quiz/{id}/submissions/"""

    def setUp(self):
        super().setUp()
        self.submissions_url = quiz_action_url(
            self.course.course_code, self.quiz.pk, "submissions"
        )
        QuizSubmission.objects.create(
            quiz=self.quiz,
            student=self.student_user.student_profile,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
            score=4,
        )

    def test_faculty_can_list_submissions_returns_200(self):
        r = self.client.get(self.submissions_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_admin_can_list_submissions_returns_200(self):
        r = self.client.get(self.submissions_url, **auth_header(self.admin_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_student_cannot_list_submissions_returns_403(self):
        r = self.client.get(self.submissions_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self.client.get(self.submissions_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submissions_list_contains_student_submission(self):
        r = self.client.get(self.submissions_url, **auth_header(self.faculty_user))
        self.assertEqual(len(r.data), 1)

    def test_submission_contains_score(self):
        r = self.client.get(self.submissions_url, **auth_header(self.faculty_user))
        self.assertIn("score", r.data[0])


# ---------------------------------------------------------------------------
# MyGradeTests
# ---------------------------------------------------------------------------

class MyGradeTests(QuizTestBase):
    """GET /api/v1/<course_code>/quiz/{id}/my-grade/"""

    def setUp(self):
        super().setUp()
        self.my_grade_url = quiz_action_url(
            self.course.course_code, self.quiz.pk, "my-grade"
        )

    def _submit_quiz(self, score=4):
        sub = QuizSubmission.objects.create(
            quiz=self.quiz,
            student=self.student_user.student_profile,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
            score=score,
        )
        SubmissionAnswer.objects.create(
            submission=sub, question=self.q1, selected_choice=1
        )
        SubmissionAnswer.objects.create(
            submission=sub, question=self.q2, selected_choice=2
        )
        return sub

    def test_my_grade_as_student_returns_200(self):
        self._submit_quiz()
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_my_grade_contains_score(self):
        self._submit_quiz(score=4)
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(float(r.data["score"]), 4.0)

    def test_my_grade_contains_correct_count(self):
        self._submit_quiz()
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(r.data["correct_count"], 2)

    def test_my_grade_contains_total_questions(self):
        self._submit_quiz()
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(r.data["total_questions"], 2)

    def test_my_grade_contains_total_marks(self):
        self._submit_quiz()
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(float(r.data["total_marks"]), 4.0)  # 2 questions × 2 marks each

    def test_my_grade_not_submitted_returns_404(self):
        r = self.client.get(self.my_grade_url, **auth_header(self.student_user))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_my_grade_as_faculty_returns_403(self):
        r = self.client.get(self.my_grade_url, **auth_header(self.faculty_user))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_grade_unauthenticated_returns_401(self):
        r = self.client.get(self.my_grade_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
