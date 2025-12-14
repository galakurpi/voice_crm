from django.urls import re_path
from . import consumers
from .test_consumer import TestConsumer

websocket_urlpatterns = [
    # Test endpoint first
    re_path(r'^ws/test/$', TestConsumer.as_asgi()),
    # Main endpoint
    re_path(r'^ws/voice-agent/?$', consumers.VoiceAgentConsumer.as_asgi()),
]
