# Tossatale Backend API

[![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![SimpleJWT](https://img.shields.io/badge/Auth-SimpleJWT%20%2B%20OAuth2-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)

Django 5 + Django REST Framework (DRF) backend service for the **Tossatale** digital story, essay, editorial journal, and short film publishing platform.

---

## 🌐 Live API & Documentation Endpoints
- **Live Frontend Application**: [https://tossatale.com](https://tossatale.com)
- **Production API Base**: `https://tossatale.com/api/v1/`
- **Swagger Interactive API Documentation**: `http://localhost:8000/api/docs/` (or `https://tossatale.com/api/docs/`)
- **OpenAPI Schema (JSON)**: `http://localhost:8000/api/schema/`
- **Django Administration Portal**: `http://localhost:8000/admin/`

---

## 🌟 Key Features & Ecosystem

- **Authentication & Roles**: JWT Authentication (SimpleJWT) + Google OAuth 2.0 1-Click Login. Roles: `GUEST`, `READER`, `WRITER`, `ADMIN`.
- **Granular API Rate Throttling**: Multi-tier scoped rate limiting defending against brute force & spam (`anon: 120/min`, `user: 600/min`, `auth_login: 15/min`, `auth_register: 10/min`, `auth_otp: 5/min`, `contact_submit: 10/hour`).
- **Stories & Series**: Longform rich stories, chapters, serial management, auto reading time calculations, bookmarks, claps/likes, and view counters.
- **Editorial Review Queue**: Multi-state admin approval workflows (`PENDING`, `APPROVED`, `REJECTED`, `REVISION_REQUESTED`) with feedback notes.
- **Stitched Public Homepage API**: High-performance endpoint aggregating Hero Spotlights, Featured Stories, Latest Stories, Trending Stories, Featured Blogs, Short Films, and Announcement Bar with sub-50ms Redis caching.
- **Admin Homepage Builder API**: Live section slot assignments (`STORY_SLOTS`), footer branding management, and custom announcement settings.
- **Editorial Blogs & Short Films**: Full Markdown blog management and video metadata showcase with YouTube/Vimeo embedding.
- **Transactional Emails**: Resend API integration for email verification, password reset, submission notifications, and contact forwarding.
- **Media Cloud Storage**: Cloudinary integration for secure image uploads and asset optimizations.
- **Unified Response Paradigm**: All endpoints return standard `{ success, message, data, errors }` envelopes.

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

## 🛠️ Project Architecture (18 Modular Apps)

```
tossatale-backend/
├── config/                  # Django settings (base/local/prod), WSGI/ASGI, URLs, Swagger
├── common/                  # BaseModel (UUID, soft-delete), custom permissions, responses, utils
├── apps/
│   ├── accounts/            # User authentication, JWT, Google OAuth 2.0, OTP, role state
│   ├── analytics/           # Story reads, daily page views, engagement tracking
│   ├── audit_logs/          # Administrator & writer system action audit logging
│   ├── banners/             # Promotional & announcement bar configurations
│   ├── blogs/               # Editorial journal markdown posts & categories
│   ├── categories/          # Story taxonomy (Memoir, Fiction, Travel, Essays, etc.)
│   ├── contacts/            # Public inquiries, rate-throttled contact form submissions
│   ├── engagements/         # Story bookmarks, likes/claps, and comments
│   ├── homepage/            # Stitched homepage aggregator & Admin homepage builder
│   ├── moderation/          # Editorial review queue (approve, reject, revision workflows)
│   ├── newsletters/         # Subscriber list, automated welcome & issue broadcasts
│   ├── notifications/       # In-app writer & reader notification engine
│   ├── search/              # Multi-entity vector & text search across stories, blogs, writers
│   ├── series/              # Multi-part story series & episode chapter sequencing
│   ├── settings_config/     # Site-wide settings, social links, footer configuration
│   ├── stories/             # Core story catalog, tags, reading time calculator
│   ├── videos/              # Short films, video documentary library & embeds
│   └── writers/             # Writer profiles, verification badges, editorial badges
├── tests/                   # Pytest test suite with Factory-Boy fixtures
├── Procfile                 # Production process runner for Railway
├── requirements.txt         # Python package dependencies
├── manage.py                # Django CLI management script
└── README.md
```

---

## 🧪 Testing & Code Quality

```bash
# Run backend test suite with Pytest
pytest

# Run tests with coverage report
pytest --cov=apps

# Run individual app tests
pytest apps/accounts/tests/
```

---

## 📄 License

Copyright © 2026 Tossatale. All rights reserved.
