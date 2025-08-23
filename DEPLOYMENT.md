# Railway Deployment Guide

## Pre-deployment Checklist

### ✅ Completed Fixes and Migrations

1. **Bug Fixes:**
   - Fixed invalid escape sequence in `core/forms.py` (line 27)
   - Fixed WSGI path mismatch in `Procfile` and `railway.json`
   - Fixed `ROOT_URLCONF` and `WSGI_APPLICATION` settings

2. **Database Migration:**
   - Configured PostgreSQL settings with environment variables
   - Added SSL support for production database connections
   - Removed hardcoded database credentials

3. **Security Improvements:**
   - Added environment variable support for sensitive settings
   - Configured production security headers

## Railway Deployment Steps

### 1. Environment Variables Required

Set these environment variables in your Railway project:

```
SECRET_KEY=<generate-a-long-random-secret-key>
DEBUG=False
RAILWAY_ENVIRONMENT=production
```

Railway will automatically provide PostgreSQL connection variables:
- `PGDATABASE`
- `PGUSER` 
- `PGPASSWORD`
- `PGHOST`
- `PGPORT`

### 2. Deploy to Railway

1. Connect your GitHub repository to Railway
2. Railway will automatically detect the Django app
3. Set the required environment variables
4. Deploy the application

### 3. Post-deployment Commands

After deployment, run these commands in Railway's terminal:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Local Development Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up Local PostgreSQL

Install PostgreSQL and create a database:

```sql
CREATE DATABASE susu_system_db;
CREATE USER postgres WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE susu_system_db TO postgres;
```

### 3. Environment Variables for Local Development

Create a `.env` file (not included in git):

```
DB_NAME=susu_system_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-local-secret-key
DEBUG=True
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Files Modified

1. `core/forms.py` - Fixed regex escape sequence
2. `Procfile` - Fixed WSGI path
3. `railway.json` - Fixed WSGI path
4. `susu/settings.py` - Database and security configuration
5. `requirements.txt` - Added production dependencies

## Architecture

- **Framework:** Django 5.2.4
- **Database:** PostgreSQL (via psycopg2-binary)
- **Static Files:** WhiteNoise
- **Server:** Gunicorn
- **Platform:** Railway