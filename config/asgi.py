"""Ponto de entrada ASGI (HTTP + WebSocket).

Requisições HTTP seguem para o Django tradicional; conexões WebSocket passam
pela autenticação JWT (``JWTAuthMiddleware``) e são roteadas pelos consumers
definidos em ``apps.core.routing``.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# A aplicação HTTP precisa ser criada antes de importar código que use models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.core.middleware import JWTAuthMiddleware  # noqa: E402
from apps.core.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(JWTAuthMiddleware(URLRouter(websocket_urlpatterns))),
    }
)
