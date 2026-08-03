from rest_framework.throttling import AnonRateThrottle


class DemoChatThrottle(AnonRateThrottle):
    scope = "demo_chat"
