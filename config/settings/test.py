"""Configurações da suíte de testes.

Usa SQLite em memória para que os testes NUNCA toquem o banco do Supabase.
A chave secreta é gerada em tempo de execução, pois só vale durante os testes.
"""

from django.core.management.utils import get_random_secret_key

from config.settings import base

globals().update(base.configuracoes())

SECRET_KEY = get_random_secret_key()
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # NOSONAR - só acelera testes

REST_FRAMEWORK = {
    **base.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": (),
}
