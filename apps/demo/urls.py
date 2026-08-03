from django.urls import path

from apps.demo.views import DemoChatAPIView

urlpatterns = [
    path("chat/", DemoChatAPIView.as_view(), name="demo-chat"),
]
