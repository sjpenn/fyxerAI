import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator

from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter
from core.routing import websocket_urlpatterns

# Build a test application without host origin validation for easier testing
test_application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


User = get_user_model()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ws_rejects_anonymous():
    # Anonymous connections should be rejected by consumers
    communicator = WebsocketCommunicator(test_application, "/ws/notifications/")
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db(transaction=True)
def test_ws_accepts_authenticated_session():
    from asgiref.sync import async_to_sync

    # Create a user and login via Django test client to obtain session cookie
    User.objects.create_user(
        username="wsuser",
        email="wsuser@example.com",
        password="pass1234",
    )

    client = Client()
    assert client.login(username="wsuser", password="pass1234")
    sessionid = client.cookies.get("sessionid").value

    # Pass the session cookie to the websocket handshake headers
    headers = [
        (b"cookie", f"sessionid={sessionid}".encode()),
        (b"origin", b"http://localhost:8000"),
        (b"host", b"localhost:8000"),
    ]

    # Notifications WS (does not touch DB during connect)
    notif_comm = WebsocketCommunicator(test_application, "/ws/notifications/", headers=headers)
    connected, _ = async_to_sync(notif_comm.connect)()
    assert connected is True
