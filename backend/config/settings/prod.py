from .base import *
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = ["*"]  # change later

DATABASES = {
    "default": dj_database_url.parse(
        getenv("DATABASE_URL"), conn_max_age=600, conn_health_checks=True
    )
}
