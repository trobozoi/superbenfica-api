"""Configurações de produção.

Exige ``DJANGO_SECRET_KEY`` e ``DJANGO_ALLOWED_HOSTS`` definidos, força HTTPS,
cookies seguros e HSTS. O Nginx encerra o TLS e repassa o cabeçalho
``X-Forwarded-Proto`` para a aplicação.
"""

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import ALLOWED_HOSTS, SECRET_KEY, build_postgres_config, env

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY é obrigatória em produção.")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Defina DJANGO_ALLOWED_HOSTS com hosts explícitos.")

DEBUG = False

DATABASES = {"default": build_postgres_config()}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
