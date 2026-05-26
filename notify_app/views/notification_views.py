import logging
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from notify_app.models import Notification, NotificationStatus
from notify_app.serializers import (
    NotificationCreateSerializer,
    NotificationListSerializer,
    NotificationDetailSerializer,
    NotificationRetrySerializer,
)

logger = logging.getLogger(__name__)


class NotificationCreateView(generics.CreateAPIView):
    """
    POST /api/notifications/
    Create and schedule a new notification.
    """
    serializer_class = NotificationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()  # user is pulled from request in serializer


class NotificationHistoryView(generics.ListAPIView):
    """
    GET /api/notifications/
    Paginated notification history for the authenticated user.
    Supports filtering by status and channel.
    """
    serializer_class = NotificationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "channel"]
    ordering_fields = ["scheduled_time", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(generics.RetrieveAPIView):
    """
    GET /api/notifications/<uuid:pk>/
    Full detail of a single notification.
    """
    serializer_class = NotificationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationRetryView(APIView):
    """
    POST /api/notifications/<uuid:pk>/retry/
    Manually retry a failed notification.
    Blocked if permanently failed (>= max_retries).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )

        serializer = NotificationRetrySerializer(
            data={},
            context={"notification": notification, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        logger.info(
            f"[RetryView] User {request.user.id} manually retried notification {pk}"
        )

        return Response(
            NotificationDetailSerializer(updated).data,
            status=status.HTTP_200_OK,
        )


class NotificationCancelView(APIView):
    """
    POST /api/notifications/<uuid:pk>/cancel/
    Cancel a pending/scheduled notification (revokes Celery task).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )

        if notification.status not in (
            NotificationStatus.SCHEDULED,
            NotificationStatus.PENDING,
        ):
            return Response(
                {"detail": f"Cannot cancel a notification with status '{notification.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Revoke the Celery task if we have a reference
        if notification.celery_task_id:
            from celery.app.control import Control
            from django.conf import settings
            from celery import current_app
            current_app.control.revoke(notification.celery_task_id, terminate=False)

        notification.status = NotificationStatus.CANCELLED
        notification.save(update_fields=["status", "updated_at"])

        return Response(
            {"detail": "Notification cancelled.", "id": str(notification.id)},
            status=status.HTTP_200_OK,
        )


class NotificationStatsView(APIView):
    """
    GET /api/notifications/stats/
    Summary counts per status for the current user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        stats = {
            s.value: qs.filter(status=s.value).count()
            for s in NotificationStatus
        }
        stats["total"] = qs.count()
        return Response(stats)
