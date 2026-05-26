# Notification Service — Django + Celery + Redis + PostgreSQL

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

That's it. Migrations run automatically on web startup.

---

## API Endpoints

### Auth (from your existing app)
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Register user |
| POST | `/api/auth/login/` | Login → JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |

### Notifications
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/notifications/create/` | Create & schedule a notification |
| GET | `/api/notifications/` | List notification history (paginated) |
| GET | `/api/notifications/stats/` | Status summary counts |
| GET | `/api/notifications/<uuid>/` | Detail view |
| POST | `/api/notifications/<uuid>/retry/` | Manually retry failed notification |
| POST | `/api/notifications/<uuid>/cancel/` | Cancel scheduled notification |

---

## Create Notification — Example

```http
POST /api/notifications/create/
Authorization: Bearer <access_token>

{
  "title": "Reminder",
  "message": "Don't forget your meeting!",
  "channel": "email",
  "scheduled_time": "2025-01-15T14:30:00Z"
}
```

**Validation:**
- `scheduled_time` must be **in the future** — returns 400 if not
- Supported channels: `email`, `sms`, `push`, `in_app`

---

## Notification Status Lifecycle

```
SCHEDULED → PROCESSING → DELIVERED
                ↓
             FAILED (retry 1)
                ↓
             FAILED (retry 2)
                ↓
        PERMANENTLY_FAILED (after 3 failures)
```

---

## Retry Logic

- **Auto-retry**: exponential back-off — 2, 4, 8 minutes after each failure
- **Max retries**: 3 (configurable per notification via `max_retries` field)
- After 3 failures → `permanently_failed` — no more auto-retries
- **Manual retry**: POST to `/retry/` — blocked if permanently failed

---

## Architecture

```
Client → DRF API → PostgreSQL (store notification)
                 → Celery task (eta=scheduled_time) → Redis broker
                                                    ↓
                                            Worker delivers
                                            (email/sms/push/in_app)
                                                    ↓
                                            On failure → reschedule
                                            with back-off via Redis

Celery Beat → requeue_missed_notifications (every 1 min)
              → recovers stuck/crashed tasks
```

**Services:**
- `web` — Django + DRF API
- `celery_worker` — processes delivery tasks
- `celery_beat` — periodic safety-net sweep
- `flower` — task monitoring dashboard at `:5555`
- `redis` — message broker
- `db` — PostgreSQL

---

## Security

- All notification endpoints require `IsAuthenticated` (JWT)
- Users can only see/retry **their own** notifications (queryset filtered by `user=request.user`)
- Rate limiting: 100 req/min authenticated, 20 req/min anonymous
- Past-time scheduling rejected at serializer validation level

---

## Filter & Sort

```
GET /api/notifications/?status=failed
GET /api/notifications/?channel=email
GET /api/notifications/?ordering=-scheduled_time
GET /api/notifications/?status=scheduled&ordering=scheduled_time
```

---

## Add Real Channel Handlers

In `notifications/tasks/notification_tasks.py`, replace the stub functions:

```python
def _send_email(notification):
    # sendgrid_client.send(to=notification.user.email, subject=notification.title, ...)

def _send_sms(notification):
    # twilio_client.messages.create(to=notification.user.phone, body=notification.message)
```

Any exception raised from these triggers the retry logic automatically.
