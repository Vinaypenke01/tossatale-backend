# Tossatale Backend API

Django 5 + Django REST Framework (DRF) backend service for the **Tossatale** digital story and short film publishing platform.

---

## 🌟 Key Features

- **Authentication & Roles**: JWT Authentication (SimpleJWT) + Google OAuth 2.0 1-Click Login. User roles: `GUEST`, `READER`, `WRITER`, `ADMIN`.
- **Stories & Series**: Longform stories, episodes, series management, estimated reading time calculations, bookmarks, likes, and view counters.
- **Editorial Moderation Queue**: Admin approval workflows (`PENDING`, `APPROVED`, `REJECTED`, `REVISION_REQUESTED`) with feedback notes.
- **Stitched Public Homepage API**: High-performance endpoint aggregating Hero Spotlights, Featured Stories, Latest Stories, Trending Stories, Featured Blogs, Short Films, and Announcement Bar.
- **Admin Homepage Builder API**: Live section slot assignments (`STORY_SLOTS`), footer branding management, and custom announcement settings.
- **Short Films & Video Library**: Video entity CRUD with metadata, category filtering, and status controls.
- **Caching & Async Tasks**: Redis caching with 15-minute TTL and automated invalidation, paired with Celery task queues.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (or local SQLite fallback)
- Redis Server (optional for caching & background jobs)

### 2. Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate Virtual Environment (Windows)
venv\Scripts\activate

# Activate Virtual Environment (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Run Migrations & Start Server
```bash
# Apply database migrations
python manage.py migrate

# Create admin superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Server runs on: `http://localhost:8000`

---

## 📚 API Documentation & Swagger UI

Interactive Swagger / OpenAPI docs are available out of the box:
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **OpenAPI Schema JSON**: `http://localhost:8000/api/schema/`

---

## 🚂 Production Deployment Guide (Railway)

This repository is pre-configured for 1-click deployment on [Railway](https://railway.app).

### Steps:
1. Push this codebase to GitHub repository: `https://github.com/Vinaypenke01/tossatale-backend.git`
2. Log into **Railway** (`https://railway.app`) and click **"New Project"**.
3. Select **"Deploy from GitHub repo"** and choose `Vinaypenke01/tossatale-backend`.
4. Add a **PostgreSQL** database service in Railway.
5. Add a **Redis** cache service in Railway.
6. Configure the following Environment Variables in Railway Service Settings:

| Environment Variable | Recommended Value / Description |
| :--- | :--- |
| `SECRET_KEY` | Generate a strong Django secret key |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*,.railway.app,tossatale.com` |
| `DATABASE_URL` | `${Postgres.DATABASE_URL}` (Auto-linked by Railway) |
| `REDIS_URL` | `${Redis.REDIS_URL}` (Auto-linked by Railway) |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Cloud Name |
| `CLOUDINARY_API_KEY` | Cloudinary API Key |
| `CLOUDINARY_API_SECRET` | Cloudinary API Secret |

Railway will automatically run migrations and start `gunicorn config.wsgi:application` using the included `Procfile`.

---

## 🛠️ Project Architecture

```
tossatale-backend/
├── config/             # Django settings, WSGI/ASGI, URLs, Swagger
├── common/             # Base models, custom permissions, responses, constants
├── apps/
│   ├── authentication/ # User accounts, JWT, Google OAuth 2.0
│   ├── stories/        # Stories, categories, tags, engagement stats
│   ├── series/         # Multi-part story series & chapters
│   ├── moderation/     # Admin review queue & editorial approvals
│   ├── homepage/       # Stitched homepage & Admin builder API
│   ├── blogs/          # Editorial blog posts
│   ├── videos/         # Short films & video library
│   ├── writers/        # Author profiles & verification
│   └── engagements/   # Comments, bookmarks, likes, newsletter
├── Procfile            # Production process runner for Railway
├── requirements.txt    # Python package dependencies
├── manage.py           # Django CLI management script
└── README.md
```

---

## 📄 License

Copyright © 2026 Tossatale. All rights reserved.
