"""
WebSocket routing configuration for real-time features
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Email sync WebSocket
    re_path(r'ws/email-sync/$', consumers.EmailSyncConsumer.as_asgi()),
    
    # Email notifications WebSocket
    re_path(r'ws/notifications/$', consumers.EmailNotificationConsumer.as_asgi()),
]