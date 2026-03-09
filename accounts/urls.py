from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, FacultyViewSet, me
from django.urls import path, include

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("faculty", FacultyViewSet, basename="faculty")

urlpatterns = [
    path("", include(router.urls)),
    path("me/", me, name="me"),
]
