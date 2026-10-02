"""Ponto de entrada WSGI (somente HTTP).

Útil para servidores como Gunicorn quando o WebSocket não é necessário. Para
HTTP + WebSocket use ``config.asgi`` com o Daphne.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
