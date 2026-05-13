from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenants.views import DemoNoteViewSet

router = DefaultRouter()
router.register("demo-notes", DemoNoteViewSet, basename="demo-note")

urlpatterns = [
    path("", include(router.urls)),
]
