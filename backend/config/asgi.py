import os
import dotenv
from django.core.asgi import get_asgi_application

dotenv.load_dotenv()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

# Import routing after django setup
import voice_agent.routing

class LoggingProtocolTypeRouter(ProtocolTypeRouter):
    async def __call__(self, scope, receive, send):
        # #region agent log
        print(f"[DEBUG ASGI] Protocol: {scope.get('type')}, Path: {scope.get('path')}")
        # #endregion
        return await super().__call__(scope, receive, send)

application = LoggingProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(
        voice_agent.routing.websocket_urlpatterns
    ),
})
