from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentViewSet, SubmissionViewSet

router = DefaultRouter()
router.register(r"", AssignmentViewSet, basename="assignment")

# Nested router for submissions under a specific assignment.
submission_router = DefaultRouter()
submission_router.register(r"submissions", SubmissionViewSet, basename="submission")

urlpatterns = [
    path("", include(router.urls)),
    path("<int:assignment_pk>/", include(submission_router.urls)),
]
