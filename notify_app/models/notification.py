import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SCHEDULED = "scheduled", "Scheduled"
    PROCESSING = "processing", "Processing"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    PERMANENTLY_FAILED = "permanently_failed", "Permanently Failed"
    CANCELLED = "cancelled", "Cancelled"


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    PUSH = "push", "Push"
    IN_APP = "in_app", "In-App"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )

    # Scheduling
    scheduled_time = models.DateTimeField(db_index=True)

    # Status lifecycle
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.SCHEDULED,
        db_index=True,
    )

    # Retry tracking
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    last_attempted_at = models.DateTimeField(blank=True, null=True)
    next_retry_at = models.DateTimeField(blank=True, null=True)

    # Error tracking
    last_error = models.TextField(blank=True, null=True)

    # Celery task reference
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["scheduled_time", "status"]),
            models.Index(fields=["next_retry_at", "status"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title} → {self.user.email} @ {self.scheduled_time}"

    # -------------------------
    # State helpers
    # -------------------------
    @property
    def is_retryable(self) -> bool:
        return (
            self.status in (NotificationStatus.FAILED,)
            and self.retry_count < self.max_retries
        )

    @property
    def is_permanently_failed(self) -> bool:
        return self.status == NotificationStatus.PERMANENTLY_FAILED

    def mark_processing(self):
        self.status = NotificationStatus.PROCESSING
        self.last_attempted_at = timezone.now()
        self.save(update_fields=["status", "last_attempted_at", "updated_at"])

    def mark_delivered(self):
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.retry_count = 0
        self.last_error = None
        self.save(update_fields=["status", "delivered_at", "retry_count", "last_error", "updated_at"])

    def mark_failed(self, error: str = ""):
        self.retry_count += 1
        self.last_error = error
        self.last_attempted_at = timezone.now()

        if self.retry_count >= self.max_retries:
            self.status = NotificationStatus.PERMANENTLY_FAILED
            self.next_retry_at = None
        else:
            self.status = NotificationStatus.FAILED
            # Exponential back-off: 2^retry minutes
            delay_minutes = 2 ** self.retry_count
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)

        self.save(update_fields=[
            "status", "retry_count", "last_error",
            "last_attempted_at", "next_retry_at", "updated_at",
        ])

    def reset_for_retry(self):
        """Manually triggered retry by user (resets to scheduled)."""
        if self.retry_count >= self.max_retries:
            raise ValueError("Max retries reached. Cannot retry.")
        self.status = NotificationStatus.SCHEDULED
        self.next_retry_at = None
        self.save(update_fields=["status", "next_retry_at", "updated_at"])
