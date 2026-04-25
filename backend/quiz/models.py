from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


CHOICE_OPTIONS = [
    (1, "Choice 1"),
    (2, "Choice 2"),
    (3, "Choice 3"),
    (4, "Choice 4"),
]


class Quiz(models.Model):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="quizzes",
        to_field="course_code",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Time limit in minutes — enforced server-side.",
    )
    created_by = models.ForeignKey(
        "accounts.FacultyProfile",
        on_delete=models.PROTECT,
        related_name="created_quizzes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course_id})"


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display sequence — lower values appear first.",
    )
    marks = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for a correct answer.",
    )
    choice_1 = models.CharField(max_length=500)
    choice_2 = models.CharField(max_length=500)
    choice_3 = models.CharField(max_length=500)
    choice_4 = models.CharField(max_length=500)
    correct_choice = models.PositiveIntegerField(
        choices=CHOICE_OPTIONS,
        help_text="The number (1-4) of the correct choice.",
    )

    class Meta:
        unique_together = ("quiz", "order")
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class QuizSubmission(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.PROTECT,
        related_name="quiz_submissions",
    )
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total marks earned. Null until submitted.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when the student calls /start/.",
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when the student submits answers.",
    )

    class Meta:
        unique_together = ("quiz", "student")

    def __str__(self):
        return f"{self.student_id} → {self.quiz.title}"

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Record the start time for time-limit enforcement.

        Raises ValidationError if:
        - The quiz has no questions (empty quiz protection).
        - The student has already submitted (cannot restart).
        """
        if not self.quiz.questions.exists():
            raise ValidationError(
                "Cannot start a quiz that has no questions.",
                code="empty_quiz",
            )
        if self.submitted_at is not None:
            raise ValidationError(
                "This quiz has already been submitted.",
                code="already_submitted",
            )
        if self.started_at is None:
            self.started_at = timezone.now()
            self.save(update_fields=["started_at"])

    def check_time_limit(self) -> None:
        """
        Raise ValidationError if the student's time has expired.

        Uses started_at + quiz.duration_minutes. If started_at is not set
        (submit-without-start edge case) this check is skipped because
        submit() auto-sets started_at to now() before calling this.
        """
        if self.started_at is None:
            return
        elapsed = timezone.now() - self.started_at
        limit = timezone.timedelta(minutes=self.quiz.duration_minutes)
        if elapsed > limit:
            raise ValidationError(
                "Time limit exceeded. Your submission is rejected.",
                code="time_expired",
            )

    def calculate_score(self) -> Decimal:
        """
        Sum the marks of every correctly answered question.
        Returns a Decimal so it is safe to store in DecimalField.
        """
        total = Decimal("0")
        for answer in self.answers.select_related("question"):
            if answer.is_correct:
                total += Decimal(answer.question.marks)
        return total

    def submit(self, answers: list[dict]) -> None:
        """
        Full submission flow. All business logic lives here; the view only
        calls this method.

        `answers` is a list of dicts: [{question_id: int, selected_choice: int}, ...]

        Raises ValidationError for:
        - Already submitted (double-submit guard).
        - Time limit exceeded.

        Edge cases handled internally:
        - Submit without /start/ → auto-records started_at = now().
        - Partial answers (unanswered questions) → accepted.
        """
        # Edge case #1: submit without calling /start/ first
        if self.started_at is None:
            self.start()

        # Edge case #2: already submitted
        if self.submitted_at is not None:
            raise ValidationError(
                "You have already submitted this quiz.",
                code="already_submitted",
            )

        # Edge case #3: time expired
        self.check_time_limit()

        # Validate questions
        quiz_question_ids = set(self.quiz.questions.values_list('id', flat=True))
        for item in answers:
            if item["question_id"] not in quiz_question_ids:
                raise ValidationError(
                    f"Question ID {item['question_id']} does not belong to this quiz.",
                    code="invalid_question",
                )

        # Persist answers (skip duplicates via get_or_create)
        for item in answers:
            SubmissionAnswer.objects.update_or_create(
                submission=self,
                question_id=item["question_id"],
                defaults={"selected_choice": item["selected_choice"]},
            )

        # Grade and finalise
        self.score = self.calculate_score()
        self.submitted_at = timezone.now()
        self.save(update_fields=["score", "submitted_at"])


class SubmissionAnswer(models.Model):
    submission = models.ForeignKey(
        QuizSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    selected_choice = models.PositiveIntegerField(choices=CHOICE_OPTIONS)

    class Meta:
        unique_together = ("submission", "question")

    def __str__(self):
        return (
            f"Answer: Q{self.question.order} → choice {self.selected_choice}"
            f" ({'✓' if self.is_correct else '✗'})"
        )

    @property
    def is_correct(self) -> bool:
        """True when the student's choice matches the question's correct answer."""
        return self.selected_choice == self.question.correct_choice
