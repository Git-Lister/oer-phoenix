import environ
import os
from pathlib import Path

# Initialize environment variables early
env = environ.Env()
environ.Env.read_env()  # This reads the .env file if it exists

# Base settings
BASE_DIR = Path(__file__).resolve().parent.parent

# Use a safe default in dev if DJANGO_SECRET_KEY is not set
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key")
DEBUG = env.bool("DJANGO_DEBUG") if "DJANGO_DEBUG" in os.environ else True
ROOT_URLCONF = "oer_rebirth.urls"
WSGI_APPLICATION = "oer_rebirth.wsgi.application"

# Database configuration
# Database configuration
# In Docker, DB_HOST is 'db' (service name in docker-compose).
# For local host-only experiments, prefer running manage.py inside the
# 'web' container rather than changing HOST here.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'oer_rebirth'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'db'),  # Ensure this is set to 'db' for Docker
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'pgvector.django',
    'oer_rebirth',
    'resources',
]
CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

# Static files and media configuration
STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

CSV_UPLOAD_PATH = os.path.join(BASE_DIR, 'csv_files')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25MB

# Static files configuration
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Security settings
if DEBUG:
    # Development security settings
    SECURE_SSL_REDIRECT = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
else:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://localhost')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'db+postgresql:///celery')

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'session_id'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}

# Optional local LLM configuration (for metadata enrichment, etc.)
LOCAL_LLM_URL = env("LOCAL_LLM_URL") if "LOCAL_LLM_URL" in os.environ else "http://localhost:11434"  # type: ignore[arg-type]
LOCAL_LLM_MODEL = env("LOCAL_LLM_MODEL") if "LOCAL_LLM_MODEL" in os.environ else "deepseek-r1:32b"  # type: ignore[arg-type]
LOCAL_LLM_TIMEOUT = env.int("LOCAL_LLM_TIMEOUT") if "LOCAL_LLM_TIMEOUT" in os.environ else 20  # type: ignore[arg-type]

ENABLE_LLM_ENRICHMENT = (
    env.bool("ENABLE_LLM_ENRICHMENT") if "ENABLE_LLM_ENRICHMENT" in os.environ else True  # type: ignore[arg-type]
)


