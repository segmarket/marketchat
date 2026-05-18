from django.urls import path

from apps.notifications.views import (
    NotificationReadView,
    NotificationsLatestView,
    NotificationsReadAllView,
)

urlpatterns = [
    path("latest/", NotificationsLatestView.as_view(), name="notifications-latest"),
    path("read-all/", NotificationsReadAllView.as_view(), name="notifications-read-all"),
    path("<int:pk>/read/", NotificationReadView.as_view(), name="notifications-read"),
]
