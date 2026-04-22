from .base import *
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = ["*"]  # change later

DATABASES = {
    "default": dj_database_url.parse(
        getenv("DATABASE_URL"), conn_max_age=600, conn_health_checks=True
    )
}
SPECTACULAR_SETTINGS["SERVERS"] = [
    {
        "url": "https://campus-hup-api--ahmedarafa20044.replit.app",
        "description": "Production",
    },
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": getenv("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 60,
    }
}
