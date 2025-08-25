"""
Django settings for core project - Simplified Railway Version
"""

from pathlib import Path
import os
import django
from django.core.management import execute_from_command_line


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-k-vjmc6e$8s%jl0^#buqofx&%tx1+z^4koki3g0a1k8abz+8fu')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS
ALLOWED_HOSTS = ['*']  # Allow all hosts for Railway

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

# Database Configuration - Comprehensive approach
# Railway typically provides these environment variables when you add a PostgreSQL service

def get_database_config():
    # Method 1: Try DATABASE_URL (most common)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("Found DATABASE_URL")
        # Parse DATABASE_URL manually if dj-database-url isn't working
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],  # Remove leading slash
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    
    # Method 2: Try individual PostgreSQL environment variables
    pg_host = os.environ.get('PGHOST') or os.environ.get('POSTGRES_HOST')
    if pg_host:
        print("Found PostgreSQL environment variables")
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE') or os.environ.get('POSTGRES_DB', 'railway'),
            'USER': os.environ.get('PGUSER') or os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('PGPASSWORD') or os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': pg_host,
            'PORT': os.environ.get('PGPORT') or os.environ.get('POSTGRES_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    
    # Method 3: Local development fallback
    print("Using local development database")
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'susu_system_db',
        'USER': 'postgres',
        'PASSWORD': 'GHETTOBWOY',
        'HOST': 'localhost',
        'PORT': '5432',
    }

# Get database configuration
db_config = get_database_config()
DATABASES = {'default': db_config}

# Print database info (without password)
safe_db_config = db_config.copy()
if 'PASSWORD' in safe_db_config:
    safe_db_config['PASSWORD'] = '*' * 8
print(f"Database config: {safe_db_config}")

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

# Security settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

LOGIN_REDIRECT_URL = 'dashboard'

# CSRF settings for Railway
CSRF_TRUSTED_ORIGINS = [
    'https://projectsusurepo-production.up.railway.app',
    'https://*.railway.app',
]


# Auto-migrate in production
if 'RAILWAY_ENVIRONMENT' in os.environ:
    import sys
    if 'migrate' not in sys.argv:
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'susu.settings')
            django.setup()
            from django.core.management import call_command
            call_command('migrate', verbosity=0, interactive=False)
            print("✅ Auto-migration completed")
        except Exception as e:
            print(f"❌ Auto-migration failed: {e}")