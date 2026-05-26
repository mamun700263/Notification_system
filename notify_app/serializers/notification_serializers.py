from django.utils import timezone
from rest_framework import serializers
from notify_app.models import Notification, NotificationStatus


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Used for creating a new scheduled notification."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "channel",
            "scheduled_time",
        ]
        read_only_fields = ["id"]

    def validate_scheduled_time(self, value):
        """Reject scheduled times in the past."""
        # Allow a 10-second buffer to account for network/serialization lag
        if value <= timezone.now() + timezone.timedelta(seconds=10):
            raise serializers.ValidationError(
                "Scheduled time must be in the future. "
                "Please provide a time at least a few seconds from now."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        notification = Notification.objects.create(
            user=user,
            status=NotificationStatus.SCHEDULED,
            **validated_data,
        )
        # Dispatch Celery task
        from notify_app.tasks import dispatch_notification
        task = dispatch_notification.apply_async(
            args=[str(notification.id)],
            eta=notification.scheduled_time,
        )
        notification.celery_task_id = task.id
        notification.save(update_fields=["celery_task_id"])
        return notification


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight list view."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "channel",
            "scheduled_time",
            "status",
            "retry_count",
            "created_at",
        ]
        read_only_fields = fields


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Full detail including error info."""
    is_retryable = serializers.ReadOnlyField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "channel",
            "scheduled_time",
            "status",
            "retry_count",
            "max_retries",
            "last_attempted_at",
            "next_retry_at",
            "last_error",
            "delivered_at",
            "created_at",
            "updated_at",
            "is_retryable",
            "celery_task_id",
        ]
        read_only_fields = fields


class NotificationRetrySerializer(serializers.Serializer):
    """No input needed — just trigger retry on the instance."""

    def validate(self, attrs):
        notification: Notification = self.context["notification"]

        if notification.status == NotificationStatus.PERMANENTLY_FAILED:
            raise serializers.ValidationError(
                "This notification has permanently failed after "
                f"{notification.retry_count} attempts and cannot be retried."
            )
        if notification.status == NotificationStatus.DELIVERED:
            raise serializers.ValidationError(
                "This notification has already been delivered."
            )
        if notification.status not in (
            NotificationStatus.FAILED,
            NotificationStatus.SCHEDULED,
            NotificationStatus.CANCELLED,
        ):
            raise serializers.ValidationError(
                f"Cannot retry a notification with status '{notification.status}'."
            )
        return attrs

    def save(self):
        notification: Notification = self.context["notification"]
        notification.reset_for_retry()

        # Re-schedule the task immediately
        from notify_app.tasks import dispatch_notification
        task = dispatch_notification.apply_async(args=[str(notification.id)])
        notification.celery_task_id = task.id
        notification.save(update_fields=["celery_task_id"])
        return notification
