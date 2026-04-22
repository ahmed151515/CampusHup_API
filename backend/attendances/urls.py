from rest_framework.routers import DefaultRouter
from .view import AttendanceViewsets
from django.urls import include, path

routers = DefaultRouter()

routers.register("", AttendanceViewsets, basename="attendance")

urlpatterns = [path("", include(routers.urls))]
