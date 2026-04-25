from django.contrib import admin
from .models import Quiz, Question, QuizSubmission, SubmissionAnswer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ["order", "text", "marks", "choice_1", "choice_2", "choice_3", "choice_4", "correct_choice"]


class SubmissionAnswerInline(admin.TabularInline):
    model = SubmissionAnswer
    extra = 0
    readonly_fields = ["question", "selected_choice", "is_correct"]

    def is_correct(self, obj):
        return obj.is_correct

    is_correct.boolean = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "duration_minutes", "created_by", "created_at"]
    list_filter = ["course"]
    search_fields = ["title", "course__course_code"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["quiz", "order", "text", "marks", "correct_choice"]
    list_filter = ["quiz"]
    search_fields = ["text"]
    ordering = ["quiz", "order"]


@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ["quiz", "student", "score", "started_at", "submitted_at"]
    list_filter = ["quiz"]
    readonly_fields = ["score", "started_at", "submitted_at"]
    inlines = [SubmissionAnswerInline]


@admin.register(SubmissionAnswer)
class SubmissionAnswerAdmin(admin.ModelAdmin):
    list_display = ["submission", "question", "selected_choice"]
    list_filter = ["submission__quiz"]
