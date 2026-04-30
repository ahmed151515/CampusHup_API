from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(days=30)

# Local file storage — uploads land in backend/<upload_to path>.
# Assignment files  → backend/sheets/<course_code>/file.pdf
# Submission files  → backend/sheets/submissions/<course_code>/<assignment_id>/file.pdf
# (sheets/ is a sibling of the assignments app folder)
MEDIA_ROOT = BASE_DIR
MEDIA_URL = "/media/"
