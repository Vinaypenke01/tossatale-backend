# Phase 5 — Homepage, Banners, Contact, Newsletters & Site Settings

## Scope
Admin-managed homepage section configuration, banner management, contact form, newsletter subscribe/verify/unsubscribe, global site settings — all without code redeploys.

---

## Apps to Create
- `apps/homepage/`
- `apps/banners/`
- `apps/contacts/`
- `apps/newsletters/`
- `apps/settings_config/`

---

## 5A — Homepage Sections

### `apps/homepage/models.py` (§19)

**HomepageSection**
```
Table: homepage_sections
- id (UUID)
- section_key (Enum, unique):
    HERO_BANNER, FEATURED_STORY, LATEST_STORIES, TRENDING_STORIES,
    FEATURED_BLOGS, FEATURED_WRITERS, LATEST_VIDEOS, CATEGORIES, NEWSLETTER
- title (display title override)
- is_enabled (Boolean, default True)
- display_order (PositiveInteger)
- config (JSONField — per-section overrides, e.g. count, layout type)
- updated_by (FK → User, null=True), updated_at
```

**Rules:**
- Only one row per section_key (enforced by `unique=True`)
- Admin API reads/writes these records
- Public API returns only `is_enabled=True` sections in `display_order`
- `config` JSONField can store per-section options like:
  ```json
  {"count": 6, "layout": "grid"}
  ```

---

### `apps/homepage/views.py`

**Public:**
```
GET /api/v1/public/homepage/      — Full homepage data, stitched from multiple sources
```

**Response shape (§19):**
```json
{
  "hero_banner": { "active_banner": {...} },
  "featured_story": { "story": {...} },
  "latest_stories": { "stories": [...] },
  "trending_stories": { "stories": [...] },
  "featured_blogs": { "blogs": [...] },
  "featured_writers": { "writers": [...] },
  "latest_videos": { "videos": [...] },
  "categories": { "categories": [...] },
  "newsletter": { "enabled": true }
}
```

> Cache the full homepage response in Redis for 15 minutes (`cache.set("homepage", data, 900)`)

**Admin:**
```
GET   /api/v1/admin/homepage/sections/
PATCH /api/v1/admin/homepage/sections/{id}/       — Toggle enable, update config
POST  /api/v1/admin/homepage/sections/{id}/reorder/
GET   /api/v1/admin/homepage/preview/              — Preview homepage without cache
```

---

## 5B — Banners

### `apps/banners/models.py` (§20)

**Banner**
```
Table: banners
- id (UUID)
- title, subtitle, description
- banner_type (Enum: HERO, PROMOTIONAL, NEWSLETTER, CATEGORY)
- image (Cloudinary URL), mobile_image (optional)
- cta_text, cta_url (call-to-action)
- linked_story (FK → Story, null), linked_category (FK → Category, null)
- is_active (Boolean), is_default (Boolean)
- display_order (PositiveInteger)
- start_date, end_date (schedule window)
- created_by (FK → User), created_at, updated_at
```

**Rules:**
- Only one `is_default=True` banner per `banner_type` at a time
- Active banners must have `start_date <= now <= end_date` (or no dates)

---

### Banner API Endpoints (§27, §30)

**Public:**
```
GET /api/v1/public/banners/?type=HERO    — Returns active banner for type
```

**Admin:**
```
GET    /api/v1/admin/banners/
POST   /api/v1/admin/banners/
GET    /api/v1/admin/banners/{id}/
PATCH  /api/v1/admin/banners/{id}/
DELETE /api/v1/admin/banners/{id}/
POST   /api/v1/admin/banners/{id}/activate/
POST   /api/v1/admin/banners/{id}/deactivate/
POST   /api/v1/admin/banners/{id}/set-default/
```

---

## 5C — Contact Form

### `apps/contacts/models.py` (§21)

**ContactMessage**
```
Table: contact_messages
- id (UUID)
- name, email, subject
- message (TextField)
- status (Enum: NEW, IN_PROGRESS, RESOLVED, SPAM)
- ip_address, admin_notes
- resolved_by (FK → User, null), resolved_at
- created_at, updated_at
```

---

### Contact API Endpoints

**Public:**
```
POST /api/v1/public/contact/    — Submit contact form
```

**Admin:**
```
GET   /api/v1/admin/contact/messages/
GET   /api/v1/admin/contact/messages/{id}/
PATCH /api/v1/admin/contact/messages/{id}/
POST  /api/v1/admin/contact/messages/{id}/resolve/
POST  /api/v1/admin/contact/messages/{id}/mark-spam/
```

**Celery tasks:**
```python
send_contact_form_acknowledgment_email(message_id)  # To submitter
notify_admin_new_contact_message(message_id)        # To admin email list
```

**Rate limiting:** Max 3 contact submissions per IP per hour using `django-ratelimit`.

---

## 5D — Newsletters

### `apps/newsletters/models.py` (§21)

**NewsletterSubscription**
```
Table: newsletter_subscriptions
- id (UUID)
- email (unique)
- is_verified (Boolean, default False)
- verification_token (UUID, unique)
- verification_sent_at, verified_at
- unsubscribe_token (UUID, unique)
- unsubscribed_at, created_at, updated_at
```

---

### Newsletter API Endpoints

**Public:**
```
POST /api/v1/public/newsletter/subscribe/        — Send verification email
GET  /api/v1/public/newsletter/verify/?token=... — Confirm subscription
GET  /api/v1/public/newsletter/unsubscribe/?token=...
```

**Admin:**
```
GET  /api/v1/admin/newsletter/subscriptions/
POST /api/v1/admin/newsletter/subscriptions/{id}/delete/
GET  /api/v1/admin/newsletter/export/             — CSV export of verified subscribers
```

**Celery tasks:**
```python
send_newsletter_verification_email(subscription_id)
send_newsletter_welcome_email(subscription_id)
```

---

## 5E — Site Settings

### `apps/settings_config/models.py` (§19)

**SiteSettings** (singleton model — always 1 row)
```
Table: site_settings
- id (Integer, always = 1)
- site_name, tagline, logo_url, favicon_url
- default_from_email
- footer_description, copyright_text
- social_facebook, social_instagram, social_x, social_linkedin, social_youtube
- maintenance_mode (Boolean, default False)
- maintenance_message
- contact_email
- analytics_google_id, analytics_meta_pixel
- updated_by (FK → User, null), updated_at
```

> ⚠️ Use `get_or_create(pk=1)` to always access the single row.

---

### Site Settings API Endpoints (§30)

**Public:**
```
GET /api/v1/public/settings/    — Returns logo, site name, footer, socials (no sensitive fields)
```

**Admin:**
```
GET   /api/v1/admin/settings/
PATCH /api/v1/admin/settings/
POST  /api/v1/admin/settings/maintenance/enable/
POST  /api/v1/admin/settings/maintenance/disable/
```

---

## Testing Checklist (§48)

- [ ] `test_homepage_public_response`
- [ ] `test_homepage_only_enabled_sections`
- [ ] `test_homepage_redis_cache`
- [ ] `test_admin_toggle_section`
- [ ] `test_admin_section_reorder`
- [ ] `test_banner_active_date_filter`
- [ ] `test_banner_default_uniqueness`
- [ ] `test_contact_form_submit`
- [ ] `test_contact_form_rate_limit` — 4th submission in 1 hour blocked
- [ ] `test_contact_admin_notification_email`
- [ ] `test_newsletter_subscribe`
- [ ] `test_newsletter_verify_token`
- [ ] `test_newsletter_unsubscribe_token`
- [ ] `test_newsletter_duplicate_subscribe` — returns existing unverified
- [ ] `test_newsletter_export_csv`
- [ ] `test_site_settings_singleton`
- [ ] `test_maintenance_mode_toggle`
- [ ] `test_public_settings_hides_sensitive_fields`
