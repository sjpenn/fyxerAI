"""
ASGI config for fyxerai_assistant project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fyxerai_assistant.settings")

# Initialize Django first
django.setup()

# Now import Channels components after Django is set up
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings

# Import WebSocket routing after Django is initialized
from core.routing import websocket_urlpatterns

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# In development, relax origin validation to avoid 403s from non-standard origins
if getattr(settings, 'DEBUG', False):
    websocket_app = AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
else:
    websocket_app = AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    )

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": websocket_app,
})
