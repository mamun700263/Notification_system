import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=0,           # We handle retries manually via our model logic
    acks_late=True,          # Only ACK after task completes (safer on worker crash)
    time_limit=60,           # Hard kill after 60s
    soft_time_limit=50,      # Raise SoftTimeLimitExceeded at 50s for graceful cleanup
)
def dispatch_notification(self, notification_id: str):
    """
    Main delivery task. Called at scheduled_time via ETA.
    Handles delivery, marks status, and schedules retries on failure.
    """
    from notify_app.models import Notification, NotificationStatus

    try:
        notification = Notification.objects.select_related("user").get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error(f"[dispatch_notification] Notification {notification_id} not found.")
        return

    # Guard: skip if already delivered or permanently failed
    if notification.status in (
        NotificationStatus.DELIVERED,
        NotificationStatus.PERMANENTLY_FAILED,
        NotificationStatus.CANCELLED,
    ):
        logger.info(
            f"[dispatch_notification] Skipping {notification_id} — status={notification.status}"
        )
        return

    # Guard: don't deliver to deleted/disabled users
    if notification.user.is_deleted or not notification.user.is_active:
        logger.warning(
            f"[dispatch_notification] User {notification.user.id} inactive. Cancelling {notification_id}."
        )
        notification.status = NotificationStatus.CANCELLED
        notification.save(update_fields=["status", "updated_at"])
        return

    notification.mark_processing()
    logger.info(f"[dispatch_notification] Processing {notification_id} via {notification.channel}")

    try:
        _deliver(notification)
        notification.mark_delivered()
        logger.info(f"[dispatch_notification] Delivered {notification_id}")

    except Exception as exc:
        error_msg = str(exc)
        logger.warning(
            f"[dispatch_notification] Failed {notification_id} "
            f"(attempt {notification.retry_count + 1}): {error_msg}"
        )
        notification.mark_failed(error=error_msg)

        if notification.is_retryable and notification.next_retry_at:
            # Schedule the next retry at the calculated back-off time
            dispatch_notification.apply_async(
                args=[notification_id],
                eta=notification.next_retry_at,
            )
            logger.info(
                f"[dispatch_notification] Retry {notification.retry_count}/{notification.max_retries} "
                f"scheduled for {notification.next_retry_at}"
            )
        else:
            logger.error(
                f"[dispatch_notification] {notification_id} permanently failed "
                f"after {notification.retry_count} attempts."
            )


def _deliver(notification) -> None:
    """
    Dispatch to the correct channel handler.
    Replace stubs with real integrations (SendGrid, Twilio, FCM, etc.).
    """
    from notify_app.models import NotificationChannel

    handlers = {
        NotificationChannel.EMAIL: _send_email,
        NotificationChannel.SMS: _send_sms,
        NotificationChannel.PUSH: _send_push,
        NotificationChannel.IN_APP: _send_in_app,
    }

    handler = handlers.get(notification.channel)
    if not handler:
        raise ValueError(f"No handler for channel '{notification.channel}'")

    handler(notification)


# -------------------------------------------------------
# Channel stubs — swap these for real provider SDKs
# -------------------------------------------------------

def _send_email(notification) -> None:
    """Send via email provider (e.g. SendGrid, SES)."""
    # Example: sendgrid_client.send(to=notification.user.email, ...)
    logger.debug(f"[EMAIL] → {notification.user.email}: {notification.title}")


def _send_sms(notification) -> None:
    """Send via SMS provider (e.g. Twilio)."""
    phone = getattr(notification.user, "phone", None)
    if not phone:
        raise ValueError(f"User {notification.user.id} has no phone number for SMS delivery.")
    logger.debug(f"[SMS] → {phone}: {notification.title}")


def _send_push(notification) -> None:
    """Send via push notification provider (e.g. FCM, APNs)."""
    logger.debug(f"[PUSH] → user {notification.user.id}: {notification.title}")


def _send_in_app(notification) -> None:
    """Mark as in-app — stored in DB, consumed by frontend polling/websocket."""
    logger.debug(f"[IN_APP] → user {notification.user.id}: {notification.title}")


# -------------------------------------------------------
# Periodic task: pick up missed / stuck notifications
# -------------------------------------------------------

@shared_task
def requeue_missed_notifications():
    """
    Beat task (run every minute) — safety net for:
    - Notifications stuck in 'processing' (worker crash)
    - Retries whose next_retry_at has passed but weren't re-queued
    """
    from notify_app.models import Notification, NotificationStatus

    now = timezone.now()
    stuck_cutoff = now - timezone.timedelta(minutes=5)

    # Re-queue stuck processing tasks
    stuck = Notification.objects.filter(
        status=NotificationStatus.PROCESSING,
        last_attempted_at__lt=stuck_cutoff,
    )
    for n in stuck:
        logger.warning(f"[requeue] Recovering stuck notification {n.id}")
        n.status = NotificationStatus.SCHEDULED
        n.save(update_fields=["status", "updated_at"])
        dispatch_notification.apply_async(args=[str(n.id)])

    # Re-queue overdue retries
    overdue = Notification.objects.filter(
        status=NotificationStatus.FAILED,
        next_retry_at__lte=now,
    )
    for n in overdue:
        logger.info(f"[requeue] Retrying overdue notification {n.id}")
        dispatch_notification.apply_async(args=[str(n.id)])
