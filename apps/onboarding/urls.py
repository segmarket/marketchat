from django.urls import path

from apps.onboarding.views import OnboardingDismissView, OnboardingStatusView

urlpatterns = [
    path("status/", OnboardingStatusView.as_view(), name="onboarding-status"),
    path("dismiss/", OnboardingDismissView.as_view(), name="onboarding-dismiss"),
]
