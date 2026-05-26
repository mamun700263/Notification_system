from django.urls import path
from notify_app.views import (
    NotificationCreateView,
    NotificationHistoryView,
    NotificationDetailView,
    NotificationRetryView,
    NotificationCancelView,
    NotificationStatsView,
)

app_name = "notifications"

urlpatterns = [
    # List + Create
    path("", NotificationHistoryView.as_view(), name="list"),
    path("create/", NotificationCreateView.as_view(), name="create"),

    # Stats
    path("stats/", NotificationStatsView.as_view(), name="stats"),

    # Detail actions
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="detail"),
    path("<uuid:pk>/retry/", NotificationRetryView.as_view(), name="retry"),
    path("<uuid:pk>/cancel/", NotificationCancelView.as_view(), name="cancel"),
]
