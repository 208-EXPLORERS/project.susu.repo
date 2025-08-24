"""
Django settings for core project - DEBUG VERSION
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-k-vjmc6e$8s%jl0^#buqofx&%tx1+z^4koki3g0a1k8abz+8fu')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Updated ALLOWED_HOSTS for both local and production
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.25.180']

# Add Railway domains if in production
if 'RAILWAY_ENVIRONMENT' in os.environ:
    ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'susu.urls'

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

WSGI_APPLICATION = 'susu.wsgi.application'
LOGIN_URL = 'login'

# DEBUG: Print all environment variables that might be related to database
print("=== RAILWAY DEBUG INFO ===")
print(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT')}")
print(f"DATABASE_URL exists: {'DATABASE_URL' in os.environ}")
if 'DATABASE_URL' in os.environ:
    database_url = os.environ.get('DATABASE_URL')
    # Only print first and last 10 chars for security
    print(f"DATABASE_URL preview: {database_url[:10]}...{database_url[-10:]}")

# Check for individual PostgreSQL variables
pg_vars = ['PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
for var in pg_vars:
    if var in os.environ:
        value = os.environ.get(var)
        if var == 'PGPASSWORD':
            print(f"{var}: {'*' * len(value)}")
        else:
            print(f"{var}: {value}")
    else:
        print(f"{var}: NOT SET")

print("=== END DEBUG INFO ===")

# Database Configuration with comprehensive fallback
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("Using DATABASE_URL")
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Ensure SSL for production
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}
        
elif os.environ.get('PGHOST'):
    print("Using individual PG environment variables")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE', 'railway'),
            'USER': os.environ.get('PGUSER', 'postgres'),
            'PASSWORD': os.environ.get('PGPASSWORD', ''),
            'HOST': os.environ.get('PGHOST'),
            'PORT': os.environ.get('PGPORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    print("Using local database fallback")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'susu_system_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'GHETTOBWOY'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Print final database config (without sensitive info)
final_db = DATABASES['default'].copy()
if 'PASSWORD' in final_db:
    final_db['PASSWORD'] = '*' * len(str(final_db['PASSWORD']))
print(f"Final database config: {final_db}")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

LOGIN_REDIRECT_URL = 'dashboard'

RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL')
if RAILWAY_STATIC_URL:
    ALLOWED_HOSTS.append(RAILWAY_STATIC_URL)
    ALLOWED_HOSTS.append('.railway.app')

CSRF_TRUSTED_ORIGINS = [
    'https://web-production-ded3d.up.railway.app',
    'https://*.railway.app',
]