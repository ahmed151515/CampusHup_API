from django.urls import include, path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

app_name = "v1"
urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("courses/", include("courses.urls")),
    path("<str:course_code>/attendance/", include("attendances.urls")),

    path("<str:course_code>/contents/", include("contents.urls")),

    path("<str:course_code>/quiz/", include("quiz.urls")),

    path(
        "auth/login/",
        extend_schema(tags=["auth"])(TokenObtainPairView).as_view(),
        name="token_obtain_pair",
    ),
    path(
        "auth/token/refresh/",
        extend_schema(tags=["auth"])(TokenRefreshView).as_view(),
        name="token_refresh",
    ),
    path(
        "auth/logout/",
        extend_schema(tags=["auth"])(TokenBlacklistView).as_view(),
        name="token_blacklist",
    ),
]
