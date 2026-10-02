"""Configurações comuns a todos os ambientes do Super Benfica.

Todos os valores sensíveis (chave secreta, credenciais do banco, URLs de
serviços) são lidos do arquivo ``.env`` / variáveis de ambiente por meio do
``django-environ``. Nenhuma credencial deve ser escrita neste arquivo.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def configuracoes() -> dict[str, Any]:
    """Retorna as configurações deste módulo (nomes em MAIÚSCULAS).

    Os settings de cada ambiente usam ``globals().update(base.configuracoes())``
    para herdar a base sem ``import *`` (regra S2208 do SonarQube).
    """
    return {nome: valor for nome, valor in globals().items() if nome.isupper()}


env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# -----------------------------------------------------------------------------
# Núcleo
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",
    "channels",
]

LOCAL_APPS = [
    "apps.core",
    "apps.filiais",
    "apps.usuarios",
    "apps.produtos",
    "apps.estoque",
    "apps.clientes",
    "apps.pedidos",
    "apps.relatorios",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_USER_MODEL = "usuarios.Usuario"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Banco de dados
# -----------------------------------------------------------------------------
DB_REQUIRED_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def build_postgres_config() -> dict[str, Any]:
    """Monta a configuração do PostgreSQL a partir das variáveis ``DB_*``.

    Falha com ``ImproperlyConfigured`` se alguma variável obrigatória estiver
    ausente, evitando que a aplicação suba com valores padrão inseguros.
    """
    missing = [name for name in DB_REQUIRED_VARS if not env(name, default="")]
    if missing:
        raise ImproperlyConfigured(f"Variáveis de banco ausentes no .env: {', '.join(missing)}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env("DB_HOST"),
        "PORT": env.int("DB_PORT"),
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": env("DB_SSLMODE", default="require")},
    }


# -----------------------------------------------------------------------------
# Redis: cache, Channels e Celery
# -----------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "superbenfica",
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    # Sem Redis: backends em memória (apenas para desenvolvimento/testes).
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CACHE_TTL_RELATORIOS = env.int("CACHE_TTL_RELATORIOS", default=300)

CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = not REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_BEAT_SCHEDULE = {
    "verificar-estoque-minimo": {
        "task": "apps.estoque.tasks.verificar_estoque_minimo",
        "schedule": timedelta(hours=1),
    },
    "gerar-resumo-diario": {
        "task": "apps.relatorios.tasks.gerar_resumo_diario",
        "schedule": timedelta(days=1),
    },
}

# -----------------------------------------------------------------------------
# Internacionalização
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Arquivos estáticos
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# -----------------------------------------------------------------------------
# CORS / CSRF
# -----------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS: list[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# -----------------------------------------------------------------------------
# Django REST Framework / JWT
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "600/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_DAYS", default=1)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# -----------------------------------------------------------------------------
# Documentação OpenAPI / Swagger (drf-spectacular)
# -----------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Super Benfica API",
    "DESCRIPTION": (
        "API REST do sistema de gerenciamento de supermercados **Super Benfica**.\n\n"
        "### Autenticação\n"
        "1. Obtenha um par de tokens em `POST /api/auth/token/` com e-mail e senha.\n"
        "2. Clique em **Authorize** e informe o token de acesso (`access`).\n"
        "3. Renove o token expirado em `POST /api/auth/token/refresh/`.\n\n"
        "### Perfis (roles)\n"
        "| Role | Acesso |\n"
        "|------|--------|\n"
        "| ADMIN | Tudo, em todas as filiais |\n"
        "| GERENTE | Gestão completa da própria filial e relatórios |\n"
        "| SEPARADOR | Consulta de estoque e separação de pedidos da filial |\n"
        "| CAIXA | Consulta de estoque, clientes e criação de pedidos da filial |\n"
        "| CLIENTE | Catálogo e os próprios pedidos e endereços |\n\n"
        "### Tempo real\n"
        "Eventos de pedidos e estoque são publicados no WebSocket "
        "`ws(s)://<host>/ws/lojas/<loja_id>/?token=<access>`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
    # Assets do Swagger/ReDoc servidos localmente (versão fixa, funciona offline).
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "/static/core/img/favicon.svg",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "deepLinking": True,
        "docExpansion": "list",
        "defaultModelsExpandDepth": 0,
        "syntaxHighlight": {"theme": "nord"},
    },
    "TAGS": [
        {"name": "Autenticação", "description": "Emissão e renovação de tokens JWT."},
        {"name": "Usuários", "description": "Usuários do sistema e seus perfis."},
        {"name": "Filiais", "description": "Lojas/filiais da rede."},
        {"name": "Produtos", "description": "Catálogo de produtos."},
        {"name": "Estoque", "description": "Estoque independente por filial."},
        {"name": "Clientes", "description": "Clientes e endereços de entrega."},
        {"name": "Pedidos", "description": "Pedidos, itens e fluxo de separação."},
        {"name": "Separações", "description": "Acompanhamento das separações."},
        {"name": "Relatórios", "description": "Indicadores gerenciais (em cache)."},
    ],
}

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "padrao": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "padrao"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
