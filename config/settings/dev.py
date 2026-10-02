"""Configurações de desenvolvimento local.

Usa o PostgreSQL configurado no ``.env`` (Supabase) e, quando ``REDIS_URL``
está vazio, cache/channels em memória com Celery executando de forma síncrona.
"""

from django.core.exceptions import ImproperlyConfigured

from config.settings import base

globals().update(base.configuracoes())

if not base.SECRET_KEY:
    raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY no arquivo .env.")

DEBUG = True
ALLOWED_HOSTS = base.ALLOWED_HOSTS or ["localhost", "127.0.0.1"]

DATABASES = {"default": base.build_postgres_config()}

# Necessário para servir a interface do Swagger com o login de sessão do admin.
REST_FRAMEWORK = {
    **base.REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
}
